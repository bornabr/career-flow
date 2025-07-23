# Career Flow - GitHub Copilot Instructions

<!-- Use this file to provide workspace-specific custom instructions to Copilot. For more details, visit https://code.visualstudio.com/docs/copilot/copilot-customization#_use-a-githubcopilotinstructionsmd-file -->

## Project Overview

Career Flow is a sophisticated, multi-agent AI assistant for job applications. This project follows a multi-stage incremental development roadmap, starting with a simple proof-of-concept and building up to a production-ready system. The core of the application is a Streamlit frontend that orchestrates resume and job description processing with an AI model, and then generates a tailored PDF resume using RenderCV.

## Core Technologies
- **Frontend**: Streamlit (`app.py`)
- **AI/LLM**: OpenAI (via `instructor` for structured output)
- **Data Validation**: Pydantic models (`app.py`)
- **PDF Generation**: RenderCV
- **Dependency Management**: Poetry

## Critical Workflow Rules - ALWAYS FOLLOW

### General Development Rules
1. **Incremental Development**: Always build features incrementally, completing one stage before starting the next
2. **Use Poetry**: Always use Poetry for package management and dependency handling. See `pyproject.toml` for dependencies.
3. **Avoid Verbose Code**: Always write concise, efficient code - avoid unnecessary complexity
4. **Enable User Verification**: Always ask the user to verify each stage (or even mid-stage) by providing sanity check instructions and simple tests for them to run.

### Local Development Setup
1.  **Install Dependencies**: Run `poetry install`.
2.  **Set API Keys**: Export your OpenAI API key: `export OPENAI_API_KEY='your-key-here'`.
3.  **Run the App**: Use `streamlit run app.py`.

### Stage Completion Protocol
1. **User Verification Required**: Before completing any stage, ALWAYS ask the user to verify the implementation
2. **Changelog Updates**: ALWAYS update `CHANGELOG.md` with completed features and stage progress
3. **Git Commit Process**: After user verification and before proceeding to next stage, ALWAYS ask user to commit changes
4. **Sequential Development**: NEVER start a new stage until the previous stage is verified and committed

### Development Workflow
1. Implement stage features
2. Update documentation and changelog
3. Tell user how to test the features
4. Request user verification
5. Wait for user approval
6. Ask user to commit changes to git
7. Only then proceed to next stage planning

## Development Guidelines

### Architecture & Design Principles
- **Application Flow**: The main application logic is in `app.py`. It follows this sequence:
    1.  User uploads resume and job description via Streamlit UI.
    2.  `get_completion` function sends data to OpenAI, using `instructor` to enforce a Pydantic schema (`CV` model).
    3.  The returned data is converted to a YAML structure compatible with RenderCV.
    4.  The user can edit the YAML in the UI.
    5.  On submission, the YAML is used to generate a PDF resume via the `rendercv.cli.commands.cli_command_render` function.
- Build incrementally: start simple, add complexity gradually
- Each stage builds upon the previous one
- Maintain clean, modular code that can be easily extended

### Data Models
- The Pydantic models in `app.py` (e.g., `CV`, `Sections`, `ExperienceEntry`) are critical. They define the data structure for the entire application, from the AI's output to the YAML for PDF generation.
- When modifying any resume-related logic, refer to these models first.

### Package Management & Dependencies
- **Use Poetry** for all Python package management
- Maintain `pyproject.toml` for dependency declarations
- Use `poetry install` for environment setup
- Use `poetry add` for adding new dependencies
- Group dependencies by stage/purpose in pyproject.toml
- Never use pip directly - always use Poetry commands

### Code Quality & Standards
- Use Python 3.9+ features and type hints
- Follow PEP 8 style guidelines
- Write descriptive docstrings for all functions and classes
- Include error handling and input validation
- Use async/await patterns where appropriate for API calls
- Implement proper logging for debugging and monitoring

### Documentation Standards
- Update README.md with any new features or changes
- Maintain comprehensive docstrings
- Update CHANGELOG.md for every stage completion
- Include usage examples for new features
- Document any breaking changes

### Security & Privacy Guidelines
- Never hardcode API keys or secrets
- Use environment variables for all sensitive configuration (e.g., `OPENAI_API_KEY`).
- Follow OpenAI's usage policies and rate limits
- Implement proper error handling to avoid exposing sensitive data
- Plan for data encryption in later stages
- Regular security audits of dependencies using `poetry audit`

### Version Control & Git Workflow
- Use descriptive commit messages following conventional commits
- Create feature branches for each stage development
- Always request user verification before stage completion
- Require explicit user approval before git commits
- Tag releases for each completed stage
- Maintain clean git history with meaningful commits

### AI/LLM Integration Best Practices
- The function `get_completion` in `app.py` is the primary interface with the AI model.
- The `instructor` library is used with `response_model=CV` to ensure the AI returns structured, Pydantic-validated data.
- Prompts are defined within `get_completion`. When modifying prompts, be sure to maintain the focus on generating output that conforms to the `CV` Pydantic model.
- Use OpenAI GPT-4 or GPT-4-mini based on use case requirements
- Design prompts to be modular and reusable across stages
- Include comprehensive token usage tracking and cost monitoring
- Implement retry logic with exponential backoff for API failures
- Cache responses where appropriate to reduce API costs
- Prepare architecture for multi-agent systems in later stages

### Error Handling & Monitoring
- Implement comprehensive exception handling
- Use structured logging with appropriate log levels
- Add health checks and monitoring endpoints for production stages
- Implement graceful degradation for API failures
- Add user-friendly error messages
- Monitor and alert on critical failures

### File Structure & Organization
- Use poetry project structure suggestions
- Use `samples/` directory for test data and examples
- Store generated outputs in `outputs/` directory
- Use consistent naming conventions across all files
- Keep configuration files in appropriate directories

## Communication & Verification Protocol

### Before Every Stage Completion
1. **Code Review**: Highlight key implementation decisions
2. **Documentation Check**: Confirm all docs are updated
3. **User Verification**: Explicitly ask "Is this stage ready for completion?"

### After User Verification
1. **Changelog Update**: Update CHANGELOG.md with stage completion
2. **Git Preparation**: Prepare commit with descriptive message
3. **Commit Request**: Ask user "Please commit these changes to git"
4. **Next Stage Planning**: Only after commit, plan next stage

## Stage-Specific Notes

Each stage should be treated as a complete, shippable increment. Focus on making each stage production-ready within its scope before adding complexity.

Remember: This is an incremental build project with strict quality gates. Always follow the verification protocol.
