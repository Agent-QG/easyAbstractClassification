# Abstract Keyword Classification Tool

## Overview

This Python script processes academic abstracts to determine whether specific keyword groups are mentioned or connected to each abstract. It utilizes a model (via API) to analyze each abstract and outputs a result of ‘Y’ (Yes) or ‘N’ (No) based on the presence of the keywords in the text. It also retries if results are inconsistent or if errors occur, ensuring a reliable outcome.

The project is based on LM studio. Please download the LM studio and the model.

## Features
- Concurrency: Multiple abstracts are processed concurrently using multithreading (via ThreadPoolExecutor).
- Progress Tracking: The script uses tqdm to provide progress tracking.
- Error Handling and Retries: If an API call fails or yields an invalid response, the script retries up to the configured maximum number of times (max_retries).
- Result Consistency: The script performs multiple runs on each abstract (determined by run_times) to ensure result consistency.
- Logging: Detailed logs of the processing steps are written to a log file.
- Incremental Saves: Results are periodically saved to an Excel file to prevent data loss in the event of interruptions.
- Customizable Configuration: The script is driven by a YAML configuration file (config.yaml) where users can specify parameters such as model name, keywords, temperature, and file paths.

# Usage

## Prerequisites

-	Python 3.7+
### Required Python packages:
-	requests
-	pandas
-	PyYAML
-	openpyxl
- tqdm

## Install the required packages via pip:

```bash
pip install requests pandas pyyaml openpyxl tqdm
```

## Configuration

Before running the script, ensure that your config.yaml file is properly configured with the following parameters:

```yaml
port_number: your_port_number                 # Port number for the model API
model_name: your_model_name                   # The model to use for abstract processing
keywords_list: keyword1_synonym1, keyword2_synonym2; keyword3_synonym3  # Semicolon-separated keyword groups, with similar or synonymous keywords in each group
temperature: 0.5                              # The temperature parameter for the model
file_path: abstracts.xlsx              # Path to the Excel file with abstracts
example_abstract: This is an example abstract...  # Example abstract for context
example_answer: Y,N                           # Expected answers for the example abstract
run_times: 3                                  # Number of runs to ensure consistent results
max_retries: 5                                # Maximum number of retries for each API call
```
### Explanation of keywords_list:

-	The keywords_list field should contain multiple groups of keywords, with each group separated by a semicolon (;).
-	Each group can contain similar or synonymous terms separated by commas (,). For example, "keyword1_synonym1, keyword2_synonym2" means that the system will consider both keyword1 and its related term synonym1 while evaluating the abstract.

## Running the LMstudio

Make sure the port number and model name in LM studio are the same as config.yaml.

## Running the Script

```bash
python abstract_processing.py
```

## Expected Input File Structure

The input Excel file should contain at least the following columns:
- Title: The title of the paper.
- Abstract: The abstract of the paper.

If the Processed column does not exist in the file, it will be added during the script execution to track progress.

## Output
- The script creates a copy of the original Excel file and appends new columns for each keyword group’s result (e.g., Keyword_Group_1_Response, Keyword_Group_2_Response).
- The processed results (‘Y’, ‘N’, or ‘Uncertain’) are written into these columns.
-	A log file (process_log_YYYYMMDD_HHMM.log) is generated in the working directory, capturing detailed information about the processing steps.

## Notes

- The script retries requests to the model up to max_retries if it doesn’t receive a valid response (‘Y’ or ‘N’).
- If all responses in run_times are consistent, the final result is saved. If results vary between runs, the response is marked as ‘Uncertain’.
- For large datasets, the script saves progress after processing every save_interval abstracts to prevent data loss in case of interruption.



