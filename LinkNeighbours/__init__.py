# import the main window object (mw) from aqt
from anki.cards import Card
from anki.models import NotetypeDict
from anki.notes import Note
from aqt import mw
# import all the Qt GUI library
from aqt.qt import *
# import the "show info" tool from utils.py
from aqt.utils import showInfo, tooltip

import json
import os
from enum import Flag, auto

# Global variable to store link rules
link_rules = {}

# Debug mode flag
# DEBUG_MODE = True

# Menu and submenu references
link_neighbours_menu: QMenu | None = None


class LinkDirection(Flag):
    FROM_LATTER_TO_FORMER = auto()
    FROM_FORMER_TO_LATTER = auto()


def get_notes_by_model(model_name: str, sort_field: str = None):
    """
    Get all notes of a specific model, sorted by a specified field
    :param model_name: Name of the note model/type
    :param sort_field: Field to sort by (if None, uses the model's sort field)
    :return: List of notes
    """
    if not mw.col:
        return []

    # Find the model by name
    model: NotetypeDict | None = mw.col.models.by_name(model_name)
    if not model:
        return []

    # If no sort field is specified, try to use the model's sort field
    if sort_field is None:
        # Get the sort field index from the model
        sort_field_idx = model.get('sortf', 0)  # Default to first field if no sort field specified

        # Get the field name using the index
        if 0 <= sort_field_idx < len(model['flds']):
            sort_field = model['flds'][sort_field_idx]['name']
        else:
            sort_field = "crt"  # fallback to creation time if index is invalid

    # Get all note IDs for this model
    note_ids = mw.col.find_notes(f"mid:{model['id']}")

    # Fetch the notes
    notes = []
    for nid in note_ids:
        note = mw.col.get_note(nid)
        notes.append(note)

    # Sort notes by the specified field
    if sort_field in [f['name'] for f in model['flds']]:
        # If sort_field is a custom field, sort by that field
        notes.sort(key=lambda x: x[sort_field].lower())
    else:
        # Default to sorting by creation time
        notes.sort(key=lambda x: x.id)

    return notes


def load_link_rules():
    """Load link rules from JSON file"""
    global link_rules
    current_folder = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(current_folder, "rules.json")
    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            link_rules = json.load(f)
    else:
        link_rules = {}


def save_link_rules():
    """Save link rules to JSON file"""
    global link_rules
    current_folder = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(current_folder, "rules.json")
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(link_rules, f, ensure_ascii=False, indent=4)


def link_notes(former_note, latter_note, rule_data, direction: LinkDirection):
    """
    Link current note to previous note based on forward link rules
    This applies the "forward link" rules: values from current note go to previous note
    """
    if LinkDirection.FROM_LATTER_TO_FORMER in direction and "forward_rules" in rule_data:
        for rule in rule_data["forward_rules"]:
            source_field = rule["source_field"]
            target_field = rule["target_field"]

            if source_field in latter_note and target_field in former_note:
                former_note[target_field] = latter_note[source_field]

        # Save the previous note with updated fields
        mw.col.update_note(former_note)

    if LinkDirection.FROM_FORMER_TO_LATTER in direction and "backward_rules" in rule_data:
        for rule in rule_data["backward_rules"]:
            source_field = rule["source_field"]
            target_field = rule["target_field"]

            if source_field in former_note and target_field in latter_note:
                latter_note[target_field] = former_note[source_field]

        # Save the next note with updated fields
        mw.col.update_note(latter_note)


def init_link_neighbours_menu():
    """Initialize the LinkNeighbours menu with submenu"""
    global link_neighbours_menu

    # Remove existing menu if it exists
    if link_neighbours_menu and link_neighbours_menu.menuAction() in mw.form.menuTools.actions():
        mw.form.menuTools.removeAction(link_neighbours_menu.menuAction())

    # Create main menu
    link_neighbours_menu = QMenu("LinkNeighbours", mw)

    new_rule_action = QAction("New Link Rule", mw)
    qconnect(new_rule_action.triggered, open_new_rule_dialog)
    link_neighbours_menu.addAction(new_rule_action)

    # Load and add saved rules to submenu
    load_link_rules()

    # Add separator only if there are saved rules
    if link_rules:
        link_neighbours_menu.addSeparator()

    update_link_neighbours_menu()

    # Add the main menu to tools menu
    mw.form.menuTools.addMenu(link_neighbours_menu)


def update_link_neighbours_menu():
    """Update the rules submenu with saved rules"""
    global link_neighbours_menu, link_rules

    # Clear existing dynamic rules
    actions_to_remove = []
    for action in link_neighbours_menu.actions():
        if hasattr(action, '_dynamic_rule'):
            actions_to_remove.append(action)

    for action in actions_to_remove:
        link_neighbours_menu.removeAction(action)

    # Add saved rules to submenu
    for note_type_name, _ in link_rules.items():
        rule_action = QAction(note_type_name, mw)
        rule_action._dynamic_rule = True
        qconnect(rule_action.triggered, lambda _, n=note_type_name: open_rule_editor(n))
        link_neighbours_menu.addAction(rule_action)


class NoteTemplateSelectionDialog(QDialog):
    """Dialog for selecting a note template before creating link rules"""

    def __init__(self):
        QDialog.__init__(self, mw)
        self.selected_template = None
        self.template_list = QListWidget()
        self.confirm_button = QPushButton("Confirm Selection")
        self.cancel_button = QPushButton("Cancel")
        self.setup_ui()

    def setup_ui(self):
        """Set up the dialog UI"""
        self.setWindowTitle("Select Note Template")
        self.setModal(True)

        layout = QVBoxLayout()

        # Instructions label
        instruction_label = QLabel("Please select a note template to create link rules for:")
        instruction_label.setWordWrap(True)
        layout.addWidget(instruction_label)

        # Template list
        layout.addWidget(self.template_list)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.confirm_button)
        button_layout.addWidget(self.cancel_button)
        layout.addLayout(button_layout)

        self.setLayout(layout)

        # Populate templates
        self.populate_templates()

        # Connect signals
        qconnect(self.confirm_button.clicked, self.confirm_selection)
        qconnect(self.cancel_button.clicked, self.reject)
        qconnect(self.template_list.itemDoubleClicked, self.confirm_selection)

    def populate_templates(self):
        """Populate the template list with available note types"""
        if mw.col:
            note_types = mw.col.models.all()
            for nt in note_types:
                item = QListWidgetItem(nt['name'])
                item.setData(Qt.ItemDataRole.UserRole, nt['id'])
                self.template_list.addItem(item)

    def confirm_selection(self):
        """Confirm the selected template"""
        selected_items = self.template_list.selectedItems()
        if selected_items:
            self.selected_template = selected_items[0].text()
            self.accept()


def open_new_rule_dialog():
    """Open dialog to create new link rule"""
    # First show the template selection dialog
    template_dialog = NoteTemplateSelectionDialog()
    if template_dialog.exec() == QDialog.DialogCode.Accepted:
        # If a template was selected, open the rule editor with that template
        if template_dialog.selected_template:
            dialog = LinkRuleDialog(template_name=template_dialog.selected_template)
            dialog.exec()


def open_rule_editor(note_type_name):
    """Open editor for existing rule"""
    dialog = LinkRuleDialog(note_type_name=note_type_name)
    dialog.exec()


class LinkRuleDialog(QDialog):
    """Dialog for creating/editing link rules"""

    def __init__(self, note_type_name=None, template_name=None):
        QDialog.__init__(self, mw)
        self.note_type_name = note_type_name
        self.template_name = template_name  # 新增：模板名称参数
        self.note_type_combo = QComboBox()

        self.note_type_display = QLabel()  # 显示选定的模板名称

        self.forward_rules_layout = None
        self.backward_rules_layout = None
        self.add_forward_rule_btn = None
        self.add_backward_rule_btn = None
        self.forward_source_combos = []
        self.forward_target_combos = []
        self.backward_source_combos = []
        self.backward_target_combos = []

        self.forward_group = self.create_rules_area("How to copy contents from the latter to the former",
                                                    LinkDirection.FROM_LATTER_TO_FORMER)
        self.backward_group = self.create_rules_area("How to copy contents the former to the latter",
                                                     LinkDirection.FROM_FORMER_TO_LATTER)
        self.save_button = QPushButton("Save")
        self.cancel_button = QPushButton("Cancel")
        self.setup_ui()
        if note_type_name and note_type_name in link_rules:
            self.load_rule_data(note_type_name)

    def setup_ui(self):
        """Set up the dialog UI"""
        self.setWindowTitle("Link Rule Editor")
        self.setModal(True)

        layout = QVBoxLayout()

        # Note type display (不可编辑，仅显示)
        note_type_layout = QHBoxLayout()
        note_type_layout.addWidget(QLabel("When we link 2 notes of Note Type:"))
        if self.template_name:
            self.note_type_display.setText(self.template_name)
        elif self.note_type_name:
            self.note_type_display.setText(self.note_type_name)
        else:
            self.note_type_display.setText("<No template selected>")
        note_type_layout.addWidget(self.note_type_display)
        layout.addLayout(note_type_layout)

        # Forward and backward link rules areas
        layout.addWidget(self.forward_group)
        layout.addWidget(self.backward_group)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.cancel_button)
        layout.addLayout(button_layout)

        self.setLayout(layout)

        # Connect signals
        qconnect(self.save_button.clicked, self.save_rule)
        qconnect(self.cancel_button.clicked, self.reject)

    def create_rules_area(self, title, direction: LinkDirection):
        """Create a group box for link rules"""
        group = QGroupBox(title)
        group_layout = QVBoxLayout()

        # Scroll area for rules
        scroll_area = QScrollArea()
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)

        # Add rule button
        add_rule_btn = QPushButton("Add Rule")

        # Store references to rule widgets
        if direction == LinkDirection.FROM_LATTER_TO_FORMER:  # forward
            self.forward_rules_layout = scroll_layout
            self.add_forward_rule_btn = add_rule_btn
        elif direction == LinkDirection.FROM_FORMER_TO_LATTER:  # backward
            self.backward_rules_layout = scroll_layout
            self.add_backward_rule_btn = add_rule_btn
        else:
            raise Exception(f"unexpected direction received: {direction}")

        scroll_area.setWidget(scroll_widget)
        scroll_area.setWidgetResizable(True)

        group_layout.addWidget(scroll_area)

        qconnect(add_rule_btn.clicked, lambda: self.add_rule_row(direction))
        group_layout.addWidget(add_rule_btn)

        group.setLayout(group_layout)

        return group

    def add_rule_row(self, direction: LinkDirection):
        """Add a new rule row for the specified direction (forward/backward)"""
        if direction == LinkDirection.FROM_LATTER_TO_FORMER:  # forward
            layout = self.forward_rules_layout
            source, target = "latter", "former"
        elif direction == LinkDirection.FROM_FORMER_TO_LATTER:  # backward
            layout = self.backward_rules_layout
            source, target = "former", "latter"
        else:
            raise Exception(f"unexpected direction received: {direction}")

        # Create a horizontal layout for the rule
        rule_layout = QHBoxLayout()

        # 获取当前选中的模板的字段
        current_template = self.note_type_display.text()
        fields = self.get_fields_for_template(current_template)

        # Source field combo
        source_label = QLabel(f"From (of {source}):")
        source_combo = QComboBox()
        source_combo.addItems(fields)
        source_combo.setEditable(False)

        # Target field combo
        target_label = QLabel(f"To (of {target}):")
        target_combo = QComboBox()
        target_combo.addItems(fields)
        target_combo.setEditable(False)

        # Add to layout
        rule_layout.addWidget(source_label)
        rule_layout.addWidget(source_combo)
        rule_layout.addWidget(target_label)
        rule_layout.addWidget(target_combo)

        # Remove button
        remove_btn = QPushButton("Remove")
        qconnect(remove_btn.clicked, lambda: self.remove_rule(rule_layout, layout, source_combo, target_combo, direction))
        rule_layout.addWidget(remove_btn)

        # Add stretch to fill space
        rule_layout.addStretch()

        # Add to main layout
        layout.addLayout(rule_layout)

        # Store reference to combos to update later
        if direction == LinkDirection.FROM_LATTER_TO_FORMER:  # forward
            self.forward_source_combos.append(source_combo)
            self.forward_target_combos.append(target_combo)
        else:  # backward
            self.backward_source_combos.append(source_combo)
            self.backward_target_combos.append(target_combo)

    @staticmethod
    def get_fields_for_template(template_name):
        """Get fields for a specific template"""
        if not mw.col:
            return []

        note_types = mw.col.models.all()
        for nt in note_types:
            if nt['name'] == template_name:
                return [f['name'] for f in nt['flds']]

        return []

    def remove_rule(self, rule_layout, parent_layout, source_combo, target_combo, direction: LinkDirection):
        """Remove a rule field row"""
        # Remove all widgets in the rule layout
        for i in reversed(range(rule_layout.count())):
            widget = rule_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)

        # Remove the layout from parent
        parent_layout.removeItem(rule_layout)

        if direction == LinkDirection.FROM_LATTER_TO_FORMER:
            self.forward_source_combos.remove(source_combo)
            self.forward_target_combos.remove(target_combo)
        elif direction == LinkDirection.FROM_FORMER_TO_LATTER:
            self.backward_source_combos.remove(source_combo)
            self.backward_target_combos.remove(target_combo)
        else:
            raise Exception(f"unexpected direction received: {direction}")


    def load_rule_data(self, rule_name):
        """Load existing rule data"""
        if rule_name in link_rules:
            rule_data = link_rules[rule_name]

            # Set the template in the display label
            self.note_type_display.setText(rule_data.get('note_type', ''))

            # Process both forward and backward rules using a helper function
            for (dirt_str, direction) in [('forward', LinkDirection.FROM_LATTER_TO_FORMER), ('backward', LinkDirection.FROM_FORMER_TO_LATTER)]:
                rules = rule_data.get(f'{dirt_str}_rules', [])
                for rule in rules:
                    self.add_rule_row(direction)
                    # Get the last added combos
                    source_combos, target_combos = self._get_combos_by_direction(direction)
                    if source_combos:  # 确保列表不为空
                        source_combo = source_combos[-1]
                        target_combo = target_combos[-1]

                        source_index = source_combo.findText(rule.get('source_field', ''))
                        if source_index >= 0:
                            source_combo.setCurrentIndex(source_index)

                        target_index = target_combo.findText(rule.get('target_field', ''))
                        if target_index >= 0:
                            target_combo.setCurrentIndex(target_index)

    def _get_combos_by_direction(self, direction: LinkDirection):
        """Helper method to get the appropriate combo lists based on direction"""
        if direction == LinkDirection.FROM_LATTER_TO_FORMER:  # forward
            return self.forward_source_combos, self.forward_target_combos
        else:  # backward
            return self.backward_source_combos, self.backward_target_combos

    def save_rule(self):
        """Save the rule"""
        global link_rules

        # 使用显示的模板名称作为note_type_name（如果是新建规则）
        if not self.note_type_name:
            self.note_type_name = self.note_type_display.text()

        # Collect rule data from UI elements
        forward_rules = []
        for i in range(len(self.forward_source_combos)):
            source_combo = self.forward_source_combos[i]
            target_combo = self.forward_target_combos[i]
            if source_combo.currentIndex() != -1 and target_combo.currentIndex() != -1:
                forward_rules.append({
                    "source_field": source_combo.currentText(),
                    "target_field": target_combo.currentText()
                })

        backward_rules = []
        for i in range(len(self.backward_source_combos)):
            source_combo = self.backward_source_combos[i]
            target_combo = self.backward_target_combos[i]
            if source_combo.currentIndex() != -1 and target_combo.currentIndex() != -1:
                backward_rules.append({
                    "source_field": source_combo.currentText(),
                    "target_field": target_combo.currentText()
                })

        rule_data = {
            "note_type": self.note_type_display.text(),
            "forward_rules": forward_rules,
            "backward_rules": backward_rules
        }

        link_rules[self.note_type_name] = rule_data
        save_link_rules()
        update_link_neighbours_menu()

        self.accept()


'''
# Add keyboard shortcuts for linking notes during review
def setup_review_shortcuts():
    """Setup keyboard shortcuts for linking notes during review"""
    from aqt import gui_hooks

    # def on_review_shortcuts(ease_tuple, reviewer, card):
    # This hook is for modifying the ease tuple before answering a card
    # For adding shortcuts, we should use a different hook
    # return ease_tuple

    # Actually, shortcuts should be added via the reviewer_shortcuts hook
    def on_shortcuts_shortcuts(shortcuts, reviewer):
        # Add shortcut to link with previous note
        shortcuts.append(("Shift+P", lambda: link_with_adjacent_note(reviewer, 'previous')))
        # Add shortcut to link with next note
        shortcuts.append(("Shift+N", lambda: link_with_adjacent_note(reviewer, 'next')))

    # gui_hooks.reviewer_will_answer_card.append(on_review_shortcuts)
    # gui_hooks.reviewer_shortcuts.append(on_shortcuts_shortcuts)
    gui_hooks.reviewer_did_init.append(on_shortcuts_shortcuts)
'''


def find_index(notes, note: Note):
    cur = f"{dict(note.items())}"
    i = 0
    for item in notes:
        cmp = f"{dict(item.items())}"
        if cmp == cur:
            return i
        i += 1
    raise ValueError('index out of range')


def link_with_adjacent_note(reviewer, previous_or_next, both_ways: bool = False):
    """
    Link current note with adjacent note (previous or next) in sequence
    :param reviewer: Anki reviewer object
    :param previous_or_next: 'previous' to link with previous note, 'next' to link with next note
    :param both_ways: True to copy in both ways, False only from the other note to current note
    """
    if not mw.col:
        return

    # Get current card and note
    current_card: Card = reviewer.card
    current_note: Note = current_card.note()

    # Determine the note type
    model_name = current_note.note_type()['name']

    # Check if we have rules for this note type
    if model_name not in link_rules:
        showInfo(f"No link rules defined for note type: {model_name}")
        return

    rule_data = link_rules[model_name]

    # Get all notes of this type, sorted
    all_notes = get_notes_by_model(model_name)

    # Find current note in the list
    try:
        current_index = find_index(all_notes, current_note)
    except ValueError:
        showInfo("Current note not found in sorted list")
        return

    # Process based on direction
    if previous_or_next == 'previous':
        # Check if there's a previous note
        if current_index <= 0:
            showInfo("No previous note to link to")
            return

        adjacent_note = all_notes[current_index - 1]
        direction = LinkDirection.FROM_FORMER_TO_LATTER
        if both_ways:
            direction |= LinkDirection.FROM_LATTER_TO_FORMER
        # Apply forward link rules (current note -> previous note)
        link_notes(adjacent_note, current_note, rule_data, direction)
        tooltip(f"Linked current note to previous note using '{model_name}' rules")
    elif previous_or_next == 'next':
        # Check if there's a next note
        if current_index >= len(all_notes) - 1:
            showInfo("No next note to link to")
            return

        adjacent_note = all_notes[current_index + 1]
        direction = LinkDirection.FROM_LATTER_TO_FORMER
        if both_ways:
            direction |= LinkDirection.FROM_FORMER_TO_LATTER
        # Apply backward link rules (current note -> next note)
        link_notes(current_note, adjacent_note, rule_data, direction)
        tooltip(f"Linked current note to next note using '{model_name}' rules")
    # Refresh the current card to reflect changes
    # noinspection PyProtectedMember
    reviewer._redraw_current_card()


def setup_review_context_menu():
    """Setup context menu items for linking notes during review"""
    from aqt import gui_hooks
    from aqt.qt import QAction

    def on_webview_will_show_context_menu(webview, menu):
        # Check if this is the main webview (review screen)
        if hasattr(webview, "title") and webview.title == "main webview" and mw.state == "review":
            # Add separator to distinguish our menu items
            menu.addSeparator()

            # Add "Link with Previous Note" action
            prev_action = QAction("Link by Copying from Previous Note", mw)
            prev_action.triggered.connect(lambda: link_with_adjacent_note(mw.reviewer, 'previous'))
            menu.addAction(prev_action)

            # Add "Link with Next Note" action
            next_action = QAction("Link by Copying from Next Note", mw)
            next_action.triggered.connect(lambda: link_with_adjacent_note(mw.reviewer, 'next'))
            menu.addAction(next_action)

            prev_bothways_action = QAction("Link with Previous Note (Bothways)", mw)
            prev_bothways_action.triggered.connect(lambda: link_with_adjacent_note(mw.reviewer, 'previous', True))
            menu.addAction(prev_bothways_action)

            next_bothways_action = QAction("Link with Next Note (Bothways)", mw)
            next_bothways_action.triggered.connect(lambda: link_with_adjacent_note(mw.reviewer, 'next'))
            menu.addAction(next_bothways_action)

    # Register the hook
    gui_hooks.webview_will_show_context_menu.append(on_webview_will_show_context_menu)


# Initialize the menu when addon loads
init_link_neighbours_menu()

# Setup context menu when addon loads
setup_review_context_menu()
