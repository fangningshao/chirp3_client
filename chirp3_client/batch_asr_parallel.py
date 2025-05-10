import os
import json
import glob
from typing import Dict, List, Tuple
import argh
from multiprocessing import Pool
import time
from functools import partial
import io
from contextlib import redirect_stdout
import sys

# Add parent directory to system path
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)
from run_asr_1speaker import run_asr


def process_single_file(wav_file: str, max_retries: int = 3, sample_rate: int = 24000) -> Tuple[str, str]:
    """
    Process a single WAV file with retry logic

    Returns:
        Tuple of (filename, transcription/error text)
    """
    filename = os.path.basename(wav_file)

    for attempt in range(max_retries):
        try:
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                run_asr(wav_file, sample_rate=sample_rate)

            asr_text = buffer.getvalue().strip()
            print(f"Success: {filename}")
            return filename, asr_text

        except Exception as e:
            if attempt < max_retries - 1:
                print(f"Attempt {attempt + 1} failed for {filename}: {str(e)}. Retrying...")
                time.sleep(2)  # Wait 2 seconds before retry
            else:
                error_msg = f"ERROR: Failed after {max_retries} attempts: {str(e)}"
                print(f"Final failure for {filename}: {error_msg}")
                return filename, error_msg


def process_folder(
    input_folder: str,
    output_json: str = "asr_results.jsonl",
    num_processes: int = 4,
    sample_rate: int = 24000,
) -> None:
    """
    Process all WAV files in parallel and save results to a JSONL file.
    Results are written as they come in, one JSON per line.

    Args:
        input_folder: Path to folder containing WAV files
        output_json: Path to output JSONL file
        num_processes: Number of parallel processes to use
    """
    wav_files = glob.glob(os.path.join(input_folder, "*.wav"))
    total_files = len(wav_files)
    print(f"Found {total_files} WAV files to process")

    success_count = 0
    fail_count = 0

    # Create a pool of workers and process files with imap for streaming results
    with Pool(processes=num_processes) as pool:
        # Open the output file in append mode
        with open(output_json, 'w', encoding='utf-8') as f:
            # Use imap instead of map to get results as they complete
            # for idx, (filename, text) in enumerate(pool.imap(process_single_file, wav_files), 1):
            process_file = partial(process_single_file, sample_rate=sample_rate)

            for idx, (filename, text) in enumerate(pool.imap(process_file, wav_files), 1):
                # Create result dictionary
                result = {
                    "filename": filename,
                    "text": text,
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                }

                # Write single result as JSON line
                json.dump(result, f, ensure_ascii=False)
                f.write('\n')
                f.flush()  # Ensure writing to disk

                # Update counts and progress
                if text.startswith("ERROR:"):
                    fail_count += 1
                else:
                    success_count += 1

                # Print progress
                print(f"\rProgress: {idx}/{total_files} files ({idx/total_files*100:.1f}%)", end='')

                # Print the result summary
                if text.startswith("ERROR:"):
                    print(f"\nFailed {filename}: {text[:100]}...")
                else:
                    print(f"\nProcessed {filename}: {text[:100]}...")

    print(f"\n\nProcessing complete. Results saved to {output_json}")
    print(f"Successfully processed: {success_count} files")
    print(f"Failed: {fail_count} files")

"""Usage:
{"filename": "file1.wav", "text": "transcribed text", "timestamp": "2025-04-23 10:30:45"}
{"filename": "file2.wav", "text": "ERROR: Failed after 3 attempts", "timestamp": "2025-04-23 10:30:47"}

python batch_asr.py path/to/wav/folder --output-json results.jsonl --num-processes 4
"""

if __name__ == "__main__":
    argh.dispatch_command(process_folder)
