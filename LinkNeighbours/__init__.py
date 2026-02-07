# import the main window object (mw) from aqt
from aqt import mw
# import all the Qt GUI library
from aqt.qt import *
# import the "show info" tool from utils.py
from aqt.utils import showInfo

import json

# Global variable to store connection rules
connection_rules = {}

# Menu and submenu references
link_neighbours_menu: QMenu = None


def get_notes_by_model(model_name, sort_field="crt"):
    """
    Get all notes of a specific model, sorted by a specified field
    :param model_name: Name of the note model/type
    :param sort_field: Field to sort by (default: creation time)
    :return: List of notes
    """
    if not mw.col:
        return []
    
    # Find the model by name
    model = mw.col.models.by_name(model_name)
    if not model:
        return []
    
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


def load_connection_rules():
    """Load connection rules from JSON file"""
    global connection_rules
    config_path = os.path.join(mw.pm.addonFolder(), "link_neighbours_config.json")
    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            connection_rules = json.load(f)
    else:
        connection_rules = {}


def save_connection_rules():
    """Save connection rules to JSON file"""
    global connection_rules
    config_path = os.path.join(mw.pm.addonFolder(), "link_neighbours_config.json")
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(connection_rules, f, ensure_ascii=False, indent=4)


def connect_notes_forward(current_note, previous_note, rule_data):
    """
    Connect current note to previous note based on forward connection rules
    This applies the "forward connection" rules: values from current note go to previous note
    """
    if "forward_rules" in rule_data:
        for rule in rule_data["forward_rules"]:
            source_field = rule["source_field"]
            target_field = rule["target_field"]
            
            if source_field in current_note and target_field in previous_note:
                previous_note[target_field] = current_note[source_field]
        
        # Save the previous note with updated fields
        mw.col.update_note(previous_note)


def connect_notes_backward(current_note, next_note, rule_data):
    """
    Connect current note to next note based on backward connection rules
    This applies the "backward connection" rules: values from current note go to next note
    """
    if "backward_rules" in rule_data:
        for rule in rule_data["backward_rules"]:
            source_field = rule["source_field"]
            target_field = rule["target_field"]
            
            if source_field in current_note and target_field in next_note:
                next_note[target_field] = current_note[source_field]
        
        # Save the next note with updated fields
        mw.col.update_note(next_note)


def init_link_neighbours_menu():
    """Initialize the LinkNeighbours menu with submenu"""
    global link_neighbours_menu
    
    # Remove existing menu if it exists
    if link_neighbours_menu and link_neighbours_menu.menuAction() in mw.form.menuTools.actions():
        mw.form.menuTools.removeAction(link_neighbours_menu.menuAction())
    
    # Create main menu
    link_neighbours_menu = QMenu("LinkNeighbours", mw)
    
    # Add "New Connection Rule" button
    new_rule_action = QAction("New Connection Rule", mw)
    qconnect(new_rule_action.triggered, open_new_rule_dialog)
    link_neighbours_menu.addAction(new_rule_action)

    # TODO 如果没有已经保存的规则集，则不需要显示Separator
    # Add separator
    link_neighbours_menu.addSeparator()
    
    # Load and add saved rules to submenu
    load_connection_rules()
    update_rules_menu()
    
    # Add the main menu to tools menu
    mw.form.menuTools.addMenu(link_neighbours_menu)


def update_rules_menu():
    """Update the rules submenu with saved rules"""
    global link_neighbours_menu, connection_rules
    
    # Clear existing dynamic rules
    actions_to_remove = []
    for action in link_neighbours_menu.actions():
        if hasattr(action, '_dynamic_rule'):
            actions_to_remove.append(action)
    
    for action in actions_to_remove:
        link_neighbours_menu.removeAction(action)
    
    # Add saved rules to submenu
    for rule_name, rule_data in connection_rules.items():
        rule_action = QAction(rule_name, mw)
        rule_action._dynamic_rule = True
        qconnect(rule_action.triggered, lambda _, r=rule_name: open_rule_editor(r))
        link_neighbours_menu.addAction(rule_action)


def open_new_rule_dialog():
    """Open dialog to create new connection rule"""
    dialog = ConnectionRuleDialog()
    dialog.exec()


def open_rule_editor(rule_name):
    """Open editor for existing rule"""
    dialog = ConnectionRuleDialog(rule_name)
    dialog.exec()


class ConnectionRuleDialog(QDialog):
    """Dialog for creating/editing connection rules"""
    
    def __init__(self, rule_name=None):
        QDialog.__init__(self, mw)
        self.rule_name = rule_name
        self.setup_ui()
        if rule_name and rule_name in connection_rules:
            self.load_rule_data(rule_name)
    
    def setup_ui(self):
        """Setup the dialog UI"""
        self.setWindowTitle("Connection Rule Editor")
        self.setModal(True)
        
        layout = QVBoxLayout()
        
        # Template selection
        template_layout = QHBoxLayout()
        template_label = QLabel("Note Type:")
        self.template_combo = QComboBox()
        template_layout.addWidget(template_label)
        template_layout.addWidget(self.template_combo)
        layout.addLayout(template_layout)
        
        # Populate note types
        self.populate_note_types()
        
        # Forward and backward connection areas
        self.forward_group = self.create_connection_area("Forward Connection (Previous note <- Current note)")
        self.backward_group = self.create_connection_area("Backward Connection (Current note <- Next note)")
        
        layout.addWidget(self.forward_group)
        layout.addWidget(self.backward_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        self.save_button = QPushButton("Save")
        self.cancel_button = QPushButton("Cancel")
        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.cancel_button)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
        # Connect signals
        qconnect(self.save_button.clicked, self.save_rule)
        qconnect(self.cancel_button.clicked, self.reject)
        qconnect(self.template_combo.currentTextChanged, self.on_template_changed)
    
    def populate_note_types(self):
        """Populate the note type combo box"""
        if mw.col:
            note_types = mw.col.models.all()
            for nt in note_types:
                self.template_combo.addItem(nt['name'], nt['id'])
    
    def create_connection_area(self, title):
        """Create a group box for connection rules"""
        group = QGroupBox(title)
        group_layout = QVBoxLayout()
        
        # Scroll area for rules
        scroll_area = QScrollArea()
        scroll_widget = QWidget()
        self.scroll_layout = QVBoxLayout(scroll_widget)
        
        # Store references to rule widgets
        setattr(self, f"{title.lower().split()[0]}_rules_layout", self.scroll_layout)
        
        scroll_area.setWidget(scroll_widget)
        scroll_area.setWidgetResizable(True)
        
        group_layout.addWidget(scroll_area)
        
        # Add rule button
        add_rule_btn = QPushButton("Add Rule")
        setattr(self, f"add_{title.lower().split()[0]}_rule_btn", add_rule_btn)
        qconnect(add_rule_btn.clicked, lambda: self.add_rule_field(title.lower().split()[0]))
        group_layout.addWidget(add_rule_btn)
        
        group.setLayout(group_layout)
        
        return group
    
    def on_template_changed(self, text):
        """Handle template change"""
        # Update fields based on selected template
        self.update_fields_for_template(text)
    
    def update_fields_for_template(self, template_name):
        """Update field lists based on selected template"""
        # Get the note type by name
        note_types = mw.col.models.all()
        selected_model = None
        for nt in note_types:
            if nt['name'] == template_name:
                selected_model = nt
                break
        
        if selected_model:
            # Get fields for this note type
            fields = [f['name'] for f in selected_model['flds']]
            
            # Update all field comboboxes in forward and backward rules
            self.update_field_combos(fields)
    
    def update_field_combos(self, fields):
        """Update all field comboboxes with the provided fields"""
        # Update all source and target field comboboxes in both directions
        for direction in ['forward', 'backward']:
            source_combos_attr = f"{direction}_source_combos"
            target_combos_attr = f"{direction}_target_combos"
            
            if hasattr(self, source_combos_attr):
                for combo in getattr(self, source_combos_attr):
                    combo.clear()
                    combo.addItems(fields)
            
            if hasattr(self, target_combos_attr):
                for combo in getattr(self, target_combos_attr):
                    combo.clear()
                    combo.addItems(fields)
    
    def add_rule_field(self, direction):
        """Add a new rule field row for the specified direction (forward/backward)"""
        layout = getattr(self, f"{direction}_rules_layout")
        
        # Create a horizontal layout for the rule
        rule_layout = QHBoxLayout()
        
        # Source field combo
        source_label = QLabel("From:")
        source_combo = QComboBox()
        # We'll populate this later based on selected template
        source_combo.setEditable(False)
        
        # Target field combo
        target_label = QLabel("To:")
        target_combo = QComboBox()
        # We'll populate this later based on selected template
        target_combo.setEditable(False)
        
        # Add to layout
        rule_layout.addWidget(source_label)
        rule_layout.addWidget(source_combo)
        rule_layout.addWidget(target_label)
        rule_layout.addWidget(target_combo)
        
        # Remove button
        remove_btn = QPushButton("Remove")
        qconnect(remove_btn.clicked, lambda: self.remove_rule_field(rule_layout, layout))
        rule_layout.addWidget(remove_btn)
        
        # Add stretch to fill space
        rule_layout.addStretch()
        
        # Add to main layout
        layout.addLayout(rule_layout)
        
        # Store reference to combos to update later
        setattr(self, f"{direction}_source_combos", getattr(self, f"{direction}_source_combos", []) + [source_combo])
        setattr(self, f"{direction}_target_combos", getattr(self, f"{direction}_target_combos", []) + [target_combo])
    
    def remove_rule_field(self, rule_layout, parent_layout):
        """Remove a rule field row"""
        # Remove all widgets in the rule layout
        for i in reversed(range(rule_layout.count())):
            widget = rule_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)
        
        # Remove the layout from parent
        parent_layout.removeItem(rule_layout)
    
    def load_rule_data(self, rule_name):
        """Load existing rule data"""
        if rule_name in connection_rules:
            rule_data = connection_rules[rule_name]
            
            # Set the template
            index = self.template_combo.findText(rule_data.get('note_type', ''))
            if index >= 0:
                self.template_combo.setCurrentIndex(index)
            
            # Load forward rules
            for rule in rule_data.get('forward_rules', []):
                self.add_rule_field('forward')
                # Get the last added combos
                source_combo = self.forward_source_combos[-1]
                target_combo = self.forward_target_combos[-1]
                
                source_index = source_combo.findText(rule.get('source_field', ''))
                if source_index >= 0:
                    source_combo.setCurrentIndex(source_index)
                
                target_index = target_combo.findText(rule.get('target_field', ''))
                if target_index >= 0:
                    target_combo.setCurrentIndex(target_index)
            
            # Load backward rules
            for rule in rule_data.get('backward_rules', []):
                self.add_rule_field('backward')
                # Get the last added combos
                source_combo = self.backward_source_combos[-1]
                target_combo = self.backward_target_combos[-1]
                
                source_index = source_combo.findText(rule.get('source_field', ''))
                if source_index >= 0:
                    source_combo.setCurrentIndex(source_index)
                
                target_index = target_combo.findText(rule.get('target_field', ''))
                if target_index >= 0:
                    target_combo.setCurrentIndex(target_index)
    
    def save_rule(self):
        """Save the rule"""
        global connection_rules
        
        if not self.rule_name:
            self.rule_name = self.template_combo.currentText()
        
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
            "note_type": self.template_combo.currentText(),
            "forward_rules": forward_rules,
            "backward_rules": backward_rules
        }
        
        connection_rules[self.rule_name] = rule_data
        save_connection_rules()
        update_rules_menu()
        
        self.accept()




# Add keyboard shortcuts for connecting notes during review
def setup_review_shortcuts():
    """Setup keyboard shortcuts for connecting notes during review"""
    from aqt import gui_hooks
    
    def on_review_shortcuts(shortcuts, reviewer):
        # Add shortcut to connect with previous note
        shortcuts.append(("Ctrl+Shift+P", lambda: connect_with_previous_note(reviewer)))
        # Add shortcut to connect with next note
        shortcuts.append(("Ctrl+Shift+N", lambda: connect_with_next_note(reviewer)))
    
    gui_hooks.reviewer_will_answer_card.append(on_review_shortcuts)


def connect_with_previous_note(reviewer):
    """Connect current note with the previous note in sequence"""
    if not mw.col:
        return
    
    # Get current card and note
    current_card = reviewer.card
    current_note = current_card.note()
    
    # Determine the note type
    model_name = current_note.note_type()['name']
    
    # Check if we have rules for this note type
    if model_name not in connection_rules:
        showInfo(f"No connection rules defined for note type: {model_name}")
        return
    
    rule_data = connection_rules[model_name]
    
    # Get all notes of this type, sorted
    all_notes = get_notes_by_model(model_name)
    
    # Find current note in the list
    try:
        current_index = all_notes.index(current_note)
    except ValueError:
        showInfo("Current note not found in sorted list")
        return
    
    # Check if there's a previous note
    if current_index <= 0:
        showInfo("No previous note to connect to")
        return
    
    previous_note = all_notes[current_index - 1]
    
    # Apply forward connection rules (current note -> previous note)
    connect_notes_forward(current_note, previous_note, rule_data)
    
    showInfo(f"Connected current note to previous note using '{model_name}' rules")


def connect_with_next_note(reviewer):
    """Connect current note with the next note in sequence"""
    if not mw.col:
        return
    
    # Get current card and note
    current_card = reviewer.card
    current_note = current_card.note()
    
    # Determine the note type
    model_name = current_note.note_type()['name']
    
    # Check if we have rules for this note type
    if model_name not in connection_rules:
        showInfo(f"No connection rules defined for note type: {model_name}")
        return
    
    rule_data = connection_rules[model_name]
    
    # Get all notes of this type, sorted
    all_notes = get_notes_by_model(model_name)
    
    # Find current note in the list
    try:
        current_index = all_notes.index(current_note)
    except ValueError:
        showInfo("Current note not found in sorted list")
        return
    
    # Check if there's a next note
    if current_index >= len(all_notes) - 1:
        showInfo("No next note to connect to")
        return
    
    next_note = all_notes[current_index + 1]
    
    # Apply backward connection rules (current note -> next note)
    connect_notes_backward(current_note, next_note, rule_data)
    
    showInfo(f"Connected current note to next note using '{model_name}' rules")


# Initialize the menu when addon loads
init_link_neighbours_menu()

# Setup shortcuts when addon loads
setup_review_shortcuts()
