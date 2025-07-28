# Career Flow - Environment Setup

This project uses a `.env` file for environment variables. You can set the OpenAI model and other secrets here.

## Usage
1. Copy `.env` to your local environment if not present.
2. Edit `.env` and set your desired model:

    OPENAI_MODEL=gpt-4o

   Or for a different model:

    OPENAI_MODEL=o3

3. The app will automatically use the value from `.env`.

## Example .env
```
OPENAI_MODEL=gpt-4o
```

## Requirements
- The app uses `python-dotenv` (already included in Poetry dependencies) to load environment variables.
- No need to pass model name via command line or shell; just edit `.env`.
