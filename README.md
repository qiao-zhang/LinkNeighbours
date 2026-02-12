# LinkNeighbours

LinkNeighbours is an Anki add-on that enables users to link adjacent notes of the same note type in their deck and copy content between them based on customizable rules. This is particularly useful for language learners who want to share audio, definitions, or other content between sequential notes to form a meaningful context.

## Features

- **Customizable Link Rules**: Define how content should be copied between adjacent notes (previous/next) for different note types
- **Bidirectional Linking**: Support for copying content in both directions (from former to latter and vice versa)
- **Context Menu Integration**: Easy access to linking functions during review via right-click context menu
- **Note Type Specific Rules**: Different linking rules for different note types in your collection
- **Internationalization**: Supports both English and Chinese interfaces

## Installation

1. Open Anki
2. Go to `Tools` → `Add-ons` → `Get Add-ons`
3. Enter the add-on code (to be published)
4. Restart Anki

Alternatively, you can manually install by placing the add-on files in your Anki add-ons folder.

## Usage

### Creating Link Rules

1. Go to `Tools` → `LinkNeighbours` → `New Link Rule Set`
2. Select the note type you want to create rules for
3. Define how content should be copied:
   - "From latter to former": How content flows from the next note to the current/previous note
   - "From former to latter": How content flows from the current/previous note to the next note
4. Add rules specifying source and target fields
5. Save the rule set

### Using Link Functions During Review

During a review session, you can use the following options:

- Right-click to open the context menu
- Select one of these options:
  - "Link by Copying from Previous Note": Copy content from the previous note to the current note
  - "Link by Copying from Next Note": Copy content from the next note to the current note
  - "Link with Previous Note (Bothways)": Copy content in both directions with the previous note
  - "Link with Next Note (Bothways)": Copy content in both directions with the next note

## Configuration

The add-on stores its configuration in `rules.json` in the add-on directory. Each rule set defines:

- `note_type`: The note type the rules apply to
- `forward_rules`: Rules for copying from the latter note to the former (next → previous)
- `backward_rules`: Rules for copying from the former note to the latter (previous → next)

Example configuration:
```json
{
  "Subs2Anki": {
    "note_type": "Subs2Anki",
    "forward_rules": [
      {
        "source_field": "CurrentBack",
        "target_field": "After"
      },
      {
        "source_field": "Audio",
        "target_field": "AfterAudio"
      }
    ],
    "backward_rules": [
      {
        "source_field": "CurrentBack",
        "target_field": "Before"
      },
      {
        "source_field": "Audio",
        "target_field": "BeforeAudio"
      }
    ]
  }
}
```

## Supported Fields

The add-on works with any field in your note types. Common use cases include:

- Sharing audio files between sequential cards
- Copying definitions or translations
- Linking related vocabulary
- Propagating example sentences

## Troubleshooting

- If notes are not found in the sorted list, ensure they are of the correct note type
- Make sure you have defined link rules for your note type before attempting to link notes
- Notes are sorted by their sort field as defined in the note type configuration

## Contributing

Contributions are welcome! Feel free to submit issues and pull requests on the GitHub repository.

## License

MIT License. See the LICENSE file for more information.