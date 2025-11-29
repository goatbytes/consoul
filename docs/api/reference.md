# API Reference

Complete reference documentation for the Consoul SDK.

## Consoul Class

The main SDK interface for integrating AI chat into your applications.

::: consoul.sdk.Consoul
    options:
      show_root_heading: true
      heading_level: 3

## ConsoulResponse Class

Structured response object returned by `Consoul.ask()`.

::: consoul.sdk.ConsoulResponse
    options:
      show_root_heading: true
      heading_level: 3

## Tool Registry

Manage and configure tools for AI agents.

::: consoul.ai.tools.registry.ToolRegistry
    options:
      show_root_heading: true
      heading_level: 3
      members:
        - register
        - unregister
        - get_tool
        - list_tools
        - bind_to_model
        - needs_approval
        - mark_approved

## Tool Metadata

Tool configuration and metadata structures.

::: consoul.ai.tools.base.ToolMetadata
    options:
      show_root_heading: true
      heading_level: 3

::: consoul.ai.tools.base.RiskLevel
    options:
      show_root_heading: true
      heading_level: 3

::: consoul.ai.tools.base.ToolCategory
    options:
      show_root_heading: true
      heading_level: 3

## Configuration

Configuration models for profiles and tools.

::: consoul.config.models.ConsoulConfig
    options:
      show_root_heading: true
      heading_level: 3

::: consoul.config.models.ProfileConfig
    options:
      show_root_heading: true
      heading_level: 3

::: consoul.config.models.ToolConfig
    options:
      show_root_heading: true
      heading_level: 3

## Conversation Management

::: consoul.ai.history.ConversationHistory
    options:
      show_root_heading: true
      heading_level: 3
      members:
        - add_user_message
        - add_assistant_message
        - add_system_message
        - clear
        - get_trimmed_messages
        - count_tokens

## Tool Catalog

Tool discovery and resolution utilities.

::: consoul.ai.tools.catalog.get_tool_by_name
    options:
      show_root_heading: true
      heading_level: 3

::: consoul.ai.tools.catalog.get_tools_by_risk_level
    options:
      show_root_heading: true
      heading_level: 3

::: consoul.ai.tools.catalog.get_tools_by_category
    options:
      show_root_heading: true
      heading_level: 3

::: consoul.ai.tools.catalog.get_all_tool_names
    options:
      show_root_heading: true
      heading_level: 3

::: consoul.ai.tools.catalog.get_all_category_names
    options:
      show_root_heading: true
      heading_level: 3

## Tool Discovery

::: consoul.ai.tools.discovery.discover_tools_from_directory
    options:
      show_root_heading: true
      heading_level: 3

## Next Steps

- **[Tutorial](tutorial.md)** - Learn SDK fundamentals
- **[Tools](tools.md)** - Master all 13 built-in tools
- **[Building Agents](agents.md)** - Create specialized AI agents
