# SOUL-289 Phase 2 Work In Progress Summary

**Task:** Decouple ProfileConfig from SDK core layer
**Branch:** `feat/SOUL-289-phase2-profile-extraction`
**Status:** 30% complete (3/10 Phase 2 steps)
**Last Commit:** `1ac5e95`

---

## ✅ Completed Steps (1-3)

### Step 1: TUI Profile Module & Backward Compatibility (Commit 7b0003d)

**Created:** `src/consoul/tui/profiles.py` (279 lines)
- Moved `ProfileConfig` class from `config.models`
- Moved `get_builtin_profiles()` from `config.profiles`
- Added `list_available_profiles()` and `get_profile_description()` helpers
- Used lazy imports to avoid circular dependencies

**Backward Compatibility:**
- `config/models.py`: Added `__getattr__()` to intercept `ProfileConfig` imports with deprecation warning
- `config/profiles.py`: Converted to lazy re-export module with deprecation warning
- Both emit clear migration guidance to new import paths

**Testing:** All 17 existing tests pass, no circular import issues

### Step 2: ProfileManager SDK Translation (Commit e1eed05)

**Enhanced:** `src/consoul/tui/services/profile_manager.py` (+133 lines)

Added 4 SDK translation methods:
1. `profile_to_sdk_params(profile, config) -> dict[str, Any]`
   - Converts ProfileConfig to SDK __init__ parameters
   - Extracts model, temperature, system_prompt, conversation settings
   - Returns dict ready for `Consoul(**params)` usage
   - Generates 7 parameters

2. `build_profile_system_prompt(profile, config) -> str`
   - Builds complete system prompt with environment context
   - Delegates to `build_enhanced_system_prompt()` for consistency
   - Uses profile.context settings for granular control

3. `get_conversation_kwargs(profile) -> dict[str, Any]`
   - Extracts conversation config as kwargs
   - Compatible with ConversationService initialization
   - Returns 8 conversation parameters

4. `get_model_name(profile, config) -> str`
   - Returns model name from profile or config fallback
   - Handles optional profile.model configuration

**Testing:** All 4 methods validated and working correctly

### Step 3: ConsoulTuiConfig Separation (Commit 1ac5e95)

**Modified:** `src/consoul/config/models.py` (-30 lines)
- Removed `profiles: dict[str, ProfileConfig]` field (line 1445)
- Removed `active_profile: str` field (line 1448)
- Removed `validate_active_profile()` validator
- Removed `validate_active_profile_exists()` validator
- Removed `get_active_profile()` method
- Updated docstring to reflect profile-free SDK design

**Modified:** `src/consoul/tui/config.py` (+47 lines)
- Added `profiles: dict[str, Any]` field (TUI-specific)
- Added `active_profile: str` field (TUI-specific)
- Added `validate_active_profile()` validator
- Added `validate_active_profile_exists()` validator
- Added `get_active_profile()` method
- Updated docstring to clarify TUI profile management

**Architecture:**
- SDK core (`ConsoulCoreConfig`) now operates profile-free with explicit parameters
- TUI layer (`ConsoulTuiConfig`) manages profiles as workflow convenience feature
- Clear separation between library (SDK) and application (TUI)

---

## 🔄 Current State

**Known Issues (Expected, Will Fix in Steps 4-10):**
29 mypy errors in 6 files that still reference `config.profiles`:

1. `config/profiles.py` (4 errors) - Wrapper function type issues
2. `config/loader.py` (8 errors) - Profile loading logic
3. `tui/services/profile_manager.py` (6 errors) - CRUD operations
4. `sdk/wrapper.py` (3 errors) - Profile parameter usage
5. `sdk/services/conversation.py` (2 errors) - Profile access
6. `tui/services/profile_ui_orchestrator.py` (6 errors) - UI operations

These errors are intentional placeholders showing exactly where updates are needed.

---

## 📋 Remaining Work (Steps 4-10)

### Step 4: Update Config Loader Dual-Path (2-3 hours)

**Goal:** Make `load_config()` profile-free for SDK, keep `load_tui_config()` with profiles

**Files to modify:**
- `src/consoul/config/loader.py`

**Changes needed:**
1. Create `create_sdk_default_config()` - profile-free defaults
2. Update `load_config()`:
   - Remove profile-related logic (lines 431-455)
   - Remove profile merging
   - Return `ConsoulCoreConfig` (profile-free)
   - Pop `profiles` and `active_profile` from merged dict
3. Keep `load_tui_config()` unchanged (already correct)
4. Update `load_profile()` to work with TUI config only

### Step 5: Update SDK Wrapper (1-2 hours)

**Goal:** Remove profile dependencies from SDK

**Files to modify:**
- `src/consoul/sdk/wrapper.py`

**Changes needed:**
1. Keep deprecation warning for `profile` parameter
2. If `profile` is provided:
   - Load TUI config (not core config)
   - Use `ProfileManager.profile_to_sdk_params()` for translation
   - Extract explicit parameters
3. Use explicit parameters as primary mode
4. Remove all `config.profiles` and `config.active_profile` accesses

### Step 6: Update CLI Chat Session (1-2 hours)

**Goal:** Use `load_tui_config()` and ProfileManager

**Files to modify:**
- `src/consoul/cli/chat_session.py`

**Changes needed:**
1. Import `load_tui_config` instead of `load_config`
2. Use `ProfileManager.build_profile_system_prompt()` for prompt building
3. Use `ProfileManager.get_conversation_kwargs()` for conversation setup
4. Keep profile-based workflow intact

### Step 7: Update TUI App (1-2 hours)

**Goal:** Use `load_tui_config()` and import from `tui.profiles`

**Files to modify:**
- `src/consoul/tui/app.py`

**Changes needed:**
1. Change import: `from consoul.tui.profiles import ProfileConfig`
2. Use `load_tui_config()` instead of `load_config()`
3. Verify ProfileManager usage

### Step 8: Fix All Imports (1-2 hours)

**Goal:** Update 17 files to import from correct locations

**Files needing import updates:**

**ProfileConfig imports (8 files):**
1. `src/consoul/sdk/wrapper.py` - Remove or use ProfileManager
2. `tests/config/test_tui_config.py` - Update to `tui.profiles.ProfileConfig`
3. `src/consoul/tui/widgets/profile_selector_modal.py` - Update to `tui.profiles.ProfileConfig`
4. `src/consoul/tui/widgets/profile_editor_modal.py` - Update to `tui.profiles.ProfileConfig`
5. `src/consoul/tui/utils/conversation_config_builder.py` - Update to `tui.profiles.ProfileConfig`
6. `src/consoul/tui/services/tool_rebinding_service.py` - Update to `tui.profiles.ProfileConfig`
7. `src/consoul/tui/services/system_prompt_builder.py` - Update to `tui.profiles.ProfileConfig`
8. `src/consoul/tui/app.py` - Update to `tui.profiles.ProfileConfig`

**config.profiles imports (9 files):**
1. `src/consoul/sdk/wrapper.py` - Remove or use ProfileManager
2. `src/consoul/__main__.py` - Update to `tui.profiles`
3. `tests/config/test_profiles.py` - Update to `tui.profiles`
4. `src/consoul/tui/services/profile_ui_orchestrator.py` - Update to `tui.profiles`
5. `src/consoul/tui/services/profile_manager.py` - Update to `tui.profiles`
6. `src/consoul/tui/app.py` - Update to `tui.profiles`
7. `src/consoul/config/loader.py` - Update to `tui.profiles` (TUI path only)
8. `src/consoul/config/__init__.py` - Add re-exports with deprecation
9. `examples/sdk/SIMPLIFICATION_PROPOSAL.md` - Documentation only

**Additional files with profile accesses:**
- `src/consoul/sdk/services/conversation.py` - Update to use TUI config type
- `src/consoul/tui/services/profile_ui_orchestrator.py` - Already uses TUI config

### Step 9: Update Tests (2-3 hours)

**Existing tests to update (4 files):**
1. `tests/unit/test_profile_optional.py` - Verify still passes with new architecture
2. `tests/config/test_profiles.py` - Update imports to `tui.profiles`
3. `tests/config/test_tui_config.py` - Test ConsoulTuiConfig
4. `tests/config/test_loader.py` - Test dual-path loading

**New tests to create (2 files):**
1. `tests/tui/services/test_profile_manager_sdk_translation.py`:
   - Test `profile_to_sdk_params()`
   - Test `build_profile_system_prompt()`
   - Test `get_conversation_kwargs()`
   - Test `get_model_name()`

2. `tests/config/test_backward_compatibility.py`:
   - Test importing ProfileConfig from config.models (with warning)
   - Test importing from config.profiles (with warning)
   - Verify re-exports work correctly

### Step 10: Integration Testing (1-2 hours)

**Manual testing:**
1. SDK profile-free mode:
   ```python
   from consoul import Consoul
   console = Consoul(model="gpt-4o", temperature=0.7)
   console.chat("test")
   ```

2. SDK with deprecated profile (should warn):
   ```python
   console = Consoul(profile="default")
   console.chat("test")
   ```

3. TUI app (should work unchanged):
   ```bash
   consoul  # Full TUI with profile support
   ```

4. CLI chat (should work unchanged):
   ```bash
   consoul chat --profile code-review
   ```

**Automated testing:**
- Run full test suite: `pytest tests/ -v`
- Run mypy type checking: `mypy src/consoul`
- Run ruff linting: `ruff check src/consoul tests/`

**Validation:**
- ✅ SDK works without profiles (explicit parameters only)
- ✅ TUI/CLI profile system continues functioning
- ✅ All existing tests pass
- ✅ Deprecation warnings guide users to new patterns
- ✅ No breaking changes for existing code (warnings only)

---

## 🚀 Parallel Agent Strategy

### Agent 1: Config Loader + SDK Wrapper (Steps 4-5)
**Estimated time:** 3-5 hours
**Files:** `config/loader.py`, `sdk/wrapper.py`
**Focus:** Core infrastructure for profile-free SDK

### Agent 2: CLI + TUI Updates (Steps 6-7)
**Estimated time:** 2-4 hours
**Files:** `cli/chat_session.py`, `tui/app.py`
**Focus:** TUI layer using new profile architecture

### Agent 3: Import Fixes (Step 8)
**Estimated time:** 1-2 hours
**Files:** 17 files across codebase
**Focus:** Update all import paths

### Agent 4: Tests + Validation (Steps 9-10)
**Estimated time:** 3-4 hours
**Files:** Test files, integration testing
**Focus:** Ensure everything works correctly

**Total parallel time:** 3-5 hours (vs 12-19 hours sequential)

---

## 📝 Key Architectural Decisions

1. **ProfileConfig Location:** Moved to `tui.profiles` (not `tui.config`) to emphasize it's a TUI feature, not core config

2. **ConsoulConfig Type Alias:** Kept as `ConsoulCoreConfig` for backward compatibility, but code should use explicit types

3. **Lazy Imports:** Used throughout to avoid circular dependencies between config, tui, and sdk layers

4. **Backward Compatibility:** Full support via re-exports and `__getattr__()` with clear deprecation warnings

5. **ProfileManager Role:** Enhanced to translate profiles → SDK parameters, enabling profile-free SDK while maintaining TUI convenience

---

## 🔗 Related Commits

- Phase 1 Complete: `5ad4427` (deprecation warnings, docs, examples, tests)
- Phase 2 Step 1: `7b0003d` (TUI profile module, backward compat)
- Phase 2 Step 2: `e1eed05` (ProfileManager SDK translation)
- Phase 2 Step 3: `1ac5e95` (ConsoulTuiConfig separation)

---

## 📊 Metrics

- **Lines added:** ~459 lines
- **Lines removed:** ~186 lines
- **Net change:** +273 lines
- **Files created:** 1 (tui/profiles.py)
- **Files modified:** 4 (config/models.py, config/profiles.py, tui/config.py, tui/services/profile_manager.py)
- **Tests:** 17/17 passing
- **Known mypy errors:** 29 (intentional, will resolve in Steps 4-10)
