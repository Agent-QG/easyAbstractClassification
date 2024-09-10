import yaml
import requests
import json
import pandas as pd
import logging
from tqdm import tqdm
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import shutil
import os

current_time = datetime.now().strftime("%Y%m%d_%H%M")

log_filename = f'process_log_{current_time}.log'

logging.basicConfig(filename=log_filename, level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

with open("config.yaml", "r") as file:
    config = yaml.safe_load(file)

port_number = config["port_number"]
model_name = config["model_name"]
keywords_list = config["keywords_list"]
temperature = config["temperature"]
file_path = config["file_path"]
example_abstract = config["example_abstract"]
example_answers = config["example_answer"].split(",")
run_times = config["run_times"]
max_retries = config["max_retries"]

file_copy_path = f"{os.path.splitext(file_path)[0]}_copy.xlsx"

if not os.path.exists(file_copy_path):
    shutil.copy(file_path, file_copy_path)
    logging.info(f"Created file copy: {file_copy_path}")

df = pd.read_excel(file_copy_path)

if 'Processed' not in df.columns:
    df['Processed'] = False
    df.to_excel(file_copy_path, index=False)
    logging.info(f"Added 'Processed' column and saved the file copy: {file_copy_path}")

url = f"http://127.0.0.1:{port_number}/v1/chat/completions"
headers = {
    "Content-Type": "application/json"
}

abstracts = df['Abstract']
titles = df['Title']

keyword_groups = [group.strip() for group in keywords_list.split(";")]
if len(keyword_groups) != len(example_answers):
    logging.error("The number of keyword groups does not match the number of example answers.")
    raise ValueError("The number of keyword groups does not match the number of example answers.")

for j, group in enumerate(keyword_groups):
    if f'Keyword_Group_{j + 1}_Response' not in df.columns:
        df[f'Keyword_Group_{j + 1}_Response'] = ""

def process_abstract(i, abstract, title):
    logging.info(f"Processing abstract {i + 1}/{len(abstracts)} with title: {title}")
    logging.info("-----")
    results = {}

    for j, group in enumerate(keyword_groups):
        keywords = [keyword.strip() for keyword in group.split(",")]
        basic_prompt = f"ONLY RESPONSE ONE LETTER. Read the abstract carefully and determine if the paper discusses or relates to the concepts of {', '.join(keywords)}, either explicitly or implicitly, in any context. Consider any related ideas, themes, or applications of these keywords. Respond with 'Y' if there is a mention or connection, or 'N' if there is none. The abstract is as follows: {example_abstract}"
        prompt = f"ONLY RESPONSE ONE LETTER. Read the abstract carefully and determine if the paper discusses or relates to the concepts of {', '.join(keywords)}, either explicitly or implicitly, in any context. Consider any related ideas, themes, or applications of these keywords. Respond with 'Y' if there is a mention or connection, or 'N' if there is none. The abstract is as follows: {abstract}"
        example_answer = example_answers[j].strip()

        consistent_responses = []
        for run in range(run_times):
            payload = {
                "model": model_name,
                "messages": [
                    {"role": "system", "content": "You are a researcher"},
                    {"role": "user", "content": basic_prompt},
                    {"role": "system", "content": example_answer},
                    {"role": "user", "content": prompt},
                ],
                "temperature": temperature,
                "max_tokens": -1,
                "stream": True
            }

            first_valid_char = None
            for attempt in range(max_retries):
                try:
                    response = requests.post(url, headers=headers, data=json.dumps(payload), stream=True)
                    if response.status_code == 200:
                        logging.info(f"Attempt {attempt + 1} for abstract {i + 1}, keyword group {j + 1}")
                        for line in response.iter_lines():
                            if line:
                                decoded_line = line.decode('utf-8')
                                if decoded_line.startswith("data: "):
                                    data_json = decoded_line[len("data: "):]
                                    try:
                                        data_dict = json.loads(data_json)
                                        if 'choices' in data_dict and 'delta' in data_dict['choices'][0]:
                                            content = data_dict['choices'][0]['delta'].get('content')
                                            if content:
                                                first_valid_char = next((char for char in content if char.isalpha()), None)
                                                if first_valid_char in ['Y', 'N']:
                                                    break
                                    except json.JSONDecodeError:
                                        logging.error(f"JSON decoding error for abstract {i + 1}, keyword group {j + 1}")
                                        pass
                        if first_valid_char in ['Y', 'N']:
                            break
                    else:
                        logging.error(f"Request failed for abstract {i + 1}, keyword group {j + 1} with status code: {response.status_code}")
                except requests.exceptions.RequestException as e:
                    logging.error(f"Error during request for abstract {i + 1}: {str(e)}")

            final_response = first_valid_char if first_valid_char in ['Y', 'N'] else 'N/A'
            consistent_responses.append(final_response)
            logging.info(f"Run {run + 1}/{run_times} for abstract {i + 1}, keyword group {j + 1}: {final_response}")
            logging.info("-----")

        if all(r == 'Y' for r in consistent_responses) or all(r == 'N' for r in consistent_responses):
            results[f'Keyword_Group_{j + 1}_Response'] = consistent_responses[0]
        else:
            results[f'Keyword_Group_{j + 1}_Response'] = 'Uncertain'

    return i, results

save_interval = 12
batch_results = []

with ThreadPoolExecutor(max_workers=6) as executor:
    futures = [executor.submit(process_abstract, i, abstracts[i], titles[i]) for i in range(len(abstracts)) if
               not df.at[i, 'Processed']]

    for count, future in enumerate(tqdm(as_completed(futures), total=len(futures))):
        i, result = future.result()
        for key, value in result.items():
            df.at[i, key] = value
        df.at[i, 'Processed'] = True
        batch_results.append(i)

        if count % save_interval == 0:
            df.to_excel(file_copy_path, index=False)
            logging.info(f"Saved progress at abstract {i + 1}")
            batch_results = []

if batch_results:
    df.to_excel(file_copy_path, index=False)

logging.info("Processing complete and responses saved to Excel.")
logging.info("-----")