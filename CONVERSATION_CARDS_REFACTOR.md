# Conversation List Card Refactor

## Status: In Progress

## Goal
Replace the DataTable-based conversation list with beautiful card widgets that support 2-line titles.

## Completed
- ✅ Created `ConversationCard` widget with:
  - Multi-line title support
  - Date display
  - Selection state styling
  - Hover effects
  - Click handling

- ✅ Updated `ConversationList` to use cards:
  - Replaced DataTable with VerticalScroll container
  - Updated `load_conversations()` to create cards
  - Updated `reload_conversations()` to clear and reload cards
  - Updated `search()` to work with cards
  - Added `on_conversation_card_card_clicked()` handler
  - Updated `_update_empty_state()` to check card count

## TODO
- ⏳ Update `action_rename_conversation()` to work with selected card
- ⏳ Update `action_delete_conversation()` to work with selected card
- ⏳ Update `_handle_rename()` to update card title
- ⏳ Update `_handle_delete()` to remove card
- ⏳ Remove unused DataTable imports
- ⏳ Update CSS in main.tcss for card-based layout
- ⏳ Test all functionality

## Files Modified
- `src/consoul/tui/widgets/conversation_card.py` (new)
- `src/consoul/tui/widgets/conversation_list.py` (modified)

## Next Steps
1. Complete the rename/delete actions to work with cards
2. Remove DataTable-specific code
3. Test the card-based UI
4. Commit changes
