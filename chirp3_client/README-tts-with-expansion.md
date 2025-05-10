# Step 1: ASR from wav files

```bash
python run_cloud_asr_batch.py batch wav_folder output_asr.txt
```

# Step 2: Expand writing with more topics

First collect some topics into topics-example.txt
(you can generate your own!)

Then run:

```bash
python rewrite_paragraphs.py output_asr.txt rewritten-v1-nano-300.txt -k openai-key.txt -m gpt-4.1-nano -c topics-example.txt
```

# Step 3: Rewrite for all paragraphs

## Step 3.1: Rewrite for synthetic paragraphs
```bash
python rewrite_chatting_style.py rewritten-v1-nano-300.txt rewritten-chatting-v1-4o-mini.txt -k openai-key.txt -m gpt-4o-mini
```

## Step 3.2: Rewrite for original paragraphs

```bash
python rewrite_chatting_style.py all-seed-notebook-asrs.txt rewritten-original-v1-4o-mini.txt -k openai-key.txt -m gpt-4o-mini
```

## Step 3.3: Concatenate orig+synth paragraphs.

```bash
cat disfluencies.txt rewritten-original-v1-4o-mini.txt rewritten-chatting-v1-4o-mini.txt > all-rewritten-v1-4o-mini.txt
```

# Step 4: Chunk sentences

```bash
python chunk_sentences.py all-rewritten-v1-4o-mini.txt all-rewritten-chunk-uniq.txt
```

# Step 5: Call Chirp3 for all chunked sentences

python run_chirp3_tts_batch.py batch test10.txt OUTPUT-chirp3-all-wavs --textdir OUTPUT-chirp3-all-txts

## Choose one voice (default aoede)

```bash
python run_chirp3_tts_batch.py batch all-rewritten-chunk-uniq.txt OUTPUT-chirp3-all-wavs --textdir OUTPUT-chirp3-all-txts
```

## Try multipole voices

<!-- Generate for 4 people, 100 for each: -->
```bash
python run_chirp3_tts_batch.py batch all-rewritten-chunk-uniq.txt OUTPUT-chirp3-all-wavs-100x4 --textdir OUTPUT-chirp3-all-txts-100x4  --voices=Aoede,Kore,Leda,Zephyr  --limit=100 
```

# Generate!
```bash
python run_chirp3_tts_batch.py batch all-rewritten-chunk-uniq.txt OUTPUT-chirp3-all-wavs-leda --textdir OUTPUT-chirp3-all-txts-leda  --voices=Leda --verbose  --start-idx=100

# python run_chirp3_tts_batch.py batch all-rewritten-chunk-uniq.txt OUTPUT-chirp3-all-wavs-leda --textdir OUTPUT-chirp3-all-txts-leda  --voices=Leda --verbose  --start-idx=401

python run_chirp3_tts_batch.py batch all-rewritten-chunk-uniq.txt OUTPUT-chirp3-all-wavs-aoede --textdir OUTPUT-chirp3-all-txts-aoede  --voices=Aoede --verbose  --start-idx=100
```

