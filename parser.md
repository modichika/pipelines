
The following updated workflow would look like:
1. Script parses issue title to identify the issue type (bug, chore, or feature), and area (frontend, backend, sdk or testing), assuming the default format of <type>(<area>): <title contents>. (This is the pre-filled title format when you open a new issue, and it’s the format most users follow. This is also a way to limit AI slop - if a contributor does not care enough to follow the format, we don’t need to look at the issue). If the title doesn’t match the formatting, the script adds a comment on the issue - “issue title must follow the correct format”
2. Script validates each subsection of the issue body via individual, smaller prompts. Each issue type has the following subsections:
Bug: environment, steps to reproduce, expected result, materials & reference
Chore: description
Feature:  feature, use case, current workaround
	
Our current approach is failing because our prompts are too large and we’re hitting token limits too quickly. Dividing prompts by issue subsection will mitigate this risk. In addition, we spend a lot of tokens retrieving the text from the linked sample issues. I think it would make more sense to compare the direct text of each issue subsection against sample, approved text.
If a prompt fails to execute, it’s also worth adding a retry mechanism, potentially with exponential backoff.

3. Finally, the script outputs its analysis (no change here)
