# Claude Command: Commit

This command helps you create well-formatted commits.

## Usage

To create a commit, just type:

```
/commit
```

## What This Command Does

1. It will automatically run pre-commit checks
2. Checks which files are staged with `git status`
3. Performs a `git diff` to understand what changes are being committed
4. Analyzes the diff to determine if multiple distinct logical changes are present
5. If multiple distinct changes are detected, suggests breaking the commit into multiple smaller commits
6. Select only files that are staged for commit, or stages all modified and new files if none are staged. Don't stage untracked files unless they are relevant to the commit. Ask first if unsure.
7. Only picks files that are relevant to the changes being committed
8. For each commit (or the single commit if not split), create a commit message using conventional commit format 
9. Before actually committing, always ask for confirmation. Show what you are going to commit, why you choose this grouping of lines to commit and the commit message.

## Best Practices for Commits

- **Verify before committing**: Ensure code is linted, tests are all successful, builds correctly and documentation is updated
- **Atomic commits**: Each commit should contain related changes that serve a single purpose
- **Split large changes**: If changes touch multiple concerns, split them into separate commits
- **Conventional commit format**: Use the format `<type>: <description>` where type is one of:
  - `feat`: A new feature
  - `fix`: A bug fix
  - `docs`: Documentation changes
  - `style`: Code style changes (formatting, etc)
  - `refactor`: Code changes that neither fix bugs nor add features
  - `perf`: Performance improvements
  - `test`: Adding or fixing tests
  - `chore`: Changes to the build process, tools, etc.
- **Present tense, imperative mood**: Write commit messages as commands (e.g., "add feature" not "added feature")
- **Concise first line**: Keep the first line under 50 characters

## Guidelines for Splitting Commits

When analyzing the diff, consider splitting commits based on these criteria:

1. **Different concerns**: Changes to unrelated parts of the codebase
2. **Different types of changes**: Mixing features, fixes, refactoring, etc.
3. **File patterns**: Changes to different types of files (e.g., source code vs documentation)
4. **Logical grouping**: Changes that would be easier to understand or review separately
5. **Size**: Very large changes that would be clearer if broken down
6. **Context**: Changes that provide different context or functionality
7. **Dependencies**: Changes that depend on each other should be grouped together, but unrelated changes should be split.
8. **Isolated changes**: If a change can be made independently without affecting other parts of the code, it should be its own commit. For example a
   new service that. Commit it first and commit the usage of the service in another commit.
9. **Ease of review**: If splitting the commit makes it easier for others to review and understand the changes, it should be done.
   Smaller commits are generally easier to review and understand than larger ones.
10. **Core logic vs. peripheral changes**: Core logic changes should be separate from peripheral changes like documentation updates or style fixes.
    This makes it easier to understand the main purpose of the commit

When suggesting multiple commits, the command will help you stage and commit the changes separately, ensuring each commit has a clear purpose and
message.

## Examples

Good commit message subjects:

- add user authentication system
- resolve memory leak in rendering process
- update API documentation with new endpoints
- simplify error handling logic in parser
- resolve linter warnings in component files
- improve developer tooling setup process
- implement business logic for transaction validation
- address minor styling inconsistency in header
- patch critical security vulnerability in auth flow
- reorganize component structure for better readability
- remove deprecated legacy code
- add input validation for user registration form
- resolve failing CI pipeline tests
- implement analytics tracking for user engagement
- strengthen authentication password requirements
- improve form accessibility for screen readers

Example of splitting commits:

- First commit: ✨ feat: add new solc version type definitions
- Second commit: 📝 docs: update documentation for new solc versions
- Third commit: 🔧 chore: update package.json dependencies
- Fourth commit: 🏷️ feat: add type definitions for new API endpoints
- Fifth commit: 🧵 feat: improve concurrency handling in worker threads
- Sixth commit: 🚨 fix: resolve linting issues in new code
- Seventh commit: ✅ test: add unit tests for new solc version features
- Eighth commit: 🔒️ fix: update dependencies with security vulnerabilities

## Important Notes

- By default, pre-commit checks will run to ensure code quality. No need to run them manually.
- Sometimes the checks fail, but it already applied formatting and linting fixes. In this case, you can run the command again to commit the changes
- **Pre-commit Hook Auto-fixes**: When pre-commit hooks fail but have modified files (e.g., ruff formatting), automatically detect this and:
  1. Check if files were modified by the hooks using `git diff`
  2. If files were modified, inform the user: "Pre-commit hooks have automatically fixed some issues. Re-adding the modified files..."
  3. Re-add the modified files with `git add`
  4. Retry the commit with the same message
  5. If it fails again after auto-fixes, then ask the user how to proceed
- If these checks fail, you'll be asked if you want to proceed with the commit anyway or fix the issues first
- If specific files are already staged, the command will only commit those files
- If no files are staged, it will automatically stage all modified and new files
- The commit message will be constructed based on the changes detected
- Before committing, the command will review the diff to identify if multiple commits would be more appropriate
- If suggesting multiple commits, it will help you stage and commit the changes separately
- Always reviews the commit diff to ensure the message matches the changes
- Always ask for confirmation before proceeding with the commit
- Make the commit message simple. Don't add words like "enhance" and "comprehensive." Explain in plain simple words what the change is about
- If you are not sure about the commit message, ask for clarification
- If you are not sure about the suggested commit split, ask for confirmation.
