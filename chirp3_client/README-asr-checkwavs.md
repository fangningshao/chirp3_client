# How to use ASR to check if wav files contains noise

First, activate your environment with valid requirements.

    conda activate chirp3

## Step 1: First run all ASR and save into a jsonl file
```bash
python batch_asr_parallel.py \
    work_dir/wav_files/ \
    -o work_dir/asr_results.jsonl \
    -n 8 -s 22050
```

(this file will use run_asr_1speaker.py internally.)

### If you see errors like this, adjust the "-s" parameter:

google.api_core.exceptions.InvalidArgument: 400 sample_rate_hertz (24000) in RecognitionConfig must either be omitted or match the value in the WAV header (22050).

## Step 2: Then, take the result jsonl file and align with the original script:

Take following params
    asr_jsonl: str,
    ref_dir: str, 
    output_jsonl: str, 

Usage:

```bash
python batch_compare_asr_ref.py \
    work_dir/asr_results.jsonl \
    work_dir/OUTPUT-chirp3-filtered-txts \
    work_dir/asrcompare.jsonl \
    --sort-by-similarity  --min-char-sim=0.0
```

Will see results like:

    Processing complete. Wrote 9666 results to work_dir/wav_files/asrcompare.jsonl
    Found 11 trailing invalid characters in ASR results.
    Filtered out False results with char_sim < 0.0


If you see this, it means ending hallucination is detected:

    [xxxxxx.wav] Warning: ASR detects MORE at end of reference! so   ||  so um are we missing anything for the shelter system lighting

### Step 3: finally, generate new wav folder with filtered results

```bash
python final_organize_filtered_wavs_txts.py \
    work_dir/wav_files/asrcompare-0.75.jsonl \
    work_dir/wav_files/ \
    work_dir/output-filtered-wavs \
    work_dir/output-filtered-txts \
    --min-similarity=0.75
```