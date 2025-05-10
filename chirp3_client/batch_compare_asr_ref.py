import json
import os
from typing import Set, Dict, Any, Tuple
import argh
import re

def clean_text(text: str) -> str:
    """Remove punctuation and extra spaces from text."""
    # Remove all punctuation and replace with space
    text = re.sub(r'[.,!?;:"\'’\-]', ' ', text)
    # Replace multiple spaces with single space
    text = re.sub(r'\s+', ' ', text)
    return text.strip().lower()

def get_words(text: str) -> Set[str]:
    """Get set of words from text, lowercased, no punctuation."""
    return set(clean_text(text).split())

def get_chars(text: str) -> Set[str]:
    """Get set of characters from text, lowercased, no punctuation."""
    return set(clean_text(text).replace(' ', ''))

def get_chars_bigram(text: str) -> Set[str]:
    """Get set of character bigrams from text, lowercased, no punctuation.
    Example: "Hello, world!" -> {"he", "el", "ll", "lo", "wo", "or", "rl", "ld"}
    """
    text = clean_text(text).replace(' ', '')
    return set(text[i:i+2] for i in range(len(text)-1))

def jaccard_similarity(set1: Set, set2: Set) -> float:
    """Calculate Jaccard similarity between two sets."""
    if not set1 and not set2:
        return 1.0
    intersection = len(set1 & set2)
    union = len(set1 | set2)
    return intersection / union if union > 0 else 0.0


# [^?‘’'\\–—.!;:a-zA-Z0-9"{},: _-&]+
def purify_reference(text: str) -> Tuple[str, bool]:
    """
    Purify reference text and check if it contains invalid characters.

    Returns:
        Tuple of (purified_text, is_valid)
        is_valid is False if text contains invalid characters
    """
    # Replace smart quotes with regular quotes
    text = text.replace('“', '"').replace('”', '"')
    text = text.replace('’', "'").replace('‘', "'")
    text = text.replace('…', "...")
    text = text.replace('–', '-').replace('—', '-')
    text = text.replace('\\n', ' ')

    # Check for invalid characters
    invalid_pattern = r'[^?&\'\\–—.!;:a-zA-Z0-9"{},: _-]+'
    if re.search(invalid_pattern, text):
        return text, False
    return text, True


def process_comparison(
    asr_jsonl: str,
    ref_dir: str,
    output_jsonl: str,
    sort_by_similarity: bool = False,
    min_char_sim: float = 0.5,
    min_char_sim_for_short_lines: float = 0.7,
    verbose: bool = False,
    detect_ending_noise: bool = False,
    neglect_reffile_prefix: str = 'vc_',  # strip this part of the refernce file
) -> None:
    """
    Compare ASR results with reference texts and output combined metrics.

    Args:
        asr_jsonl: Path to input ASR JSONL file
        ref_dir: Directory containing reference text files
        output_jsonl: Path to output JSONL file
        sort_by_similarity: Whether to sort results by word similarity (ascending)
        min_char_sim: Minimum character similarity threshold (default: 0.5)
    """

    print(f"Processing ASR results from {asr_jsonl}")
    print(f"Using reference texts from {ref_dir}")

    # Store results in memory for sorting
    results: List[Dict[str, Any]] = []

    # Process all files
    deleted_lines = []
    found_trailing_invalid = 0
    with open(asr_jsonl, 'r', encoding='utf-8') as fin:
        for line in fin:
            asr_result = json.loads(line)
            wav_name = asr_result['filename']
            asr_text = asr_result['text']

            txt_name = wav_name.replace('.wav', '.txt')
            if neglect_reffile_prefix:
                txt_name = txt_name.replace(neglect_reffile_prefix, '')
            txt_path = os.path.join(ref_dir, txt_name)
            sim_char = 0.0

            try:
                with open(txt_path, 'r', encoding='utf-8') as fref:
                    ref_text = fref.read().strip()

                    # Purify reference text
                    ref_text, is_valid = purify_reference(ref_text)
                    ca = clean_text(asr_text)
                    cr = clean_text(ref_text)

                    if not is_valid:
                        if verbose:
                            print(f"Warning: Invalid characters in reference text for {wav_name}")
                        sim_word = 0.0
                        sim_char = 0.0
                    elif (ca.startswith(cr) and not cr.startswith(ca)) and detect_ending_noise:
                        print(f"[{wav_name}] Warning: ASR detects MORE at end of reference!", ca[:-len(cr)], ' || ', cr)
                        sim_word = 0.0
                        sim_char = 0.0
                        found_trailing_invalid += 1
                    elif "my name is" in ref_text:
                        sim_word = 0.0
                        sim_char = 0.0
                        # remove personality
                    else:
                        sim_word = jaccard_similarity(get_words(asr_text), get_words(ref_text))
                        sim_char = jaccard_similarity(get_chars_bigram(asr_text), get_chars_bigram(ref_text))
            except FileNotFoundError:
                print(f"Warning: Reference file not found: {txt_path}")
                continue

            # Apply character similarity filter
            result = {
                **asr_result,
                'reference_text': ref_text,
                'sim_word': sim_word,
                'sim_char': sim_char,
                'is_valid_reference': is_valid,
            }

            if sim_char >= min_char_sim:
                if sim_char < min_char_sim_for_short_lines and len(ref_text) < 16:
                    deleted_lines.append(result)
                    continue  # Skip short references with low similarity
                results.append(result)
                if verbose:
                    print(f"Processed {wav_name}: word_sim={sim_word:.3f}, char_sim={sim_char:.3f}")
            else:
                deleted_lines.append(result)

    # Sort results if requested
    if sort_by_similarity:
        results.sort(key=lambda x: x['sim_char'])
        deleted_lines.sort(key=lambda x: x['sim_char'])

    # Write filtered and optionally sorted results
    with open(output_jsonl, 'w', encoding='utf-8') as fout:
        for result in results:
            json.dump(result, fout, ensure_ascii=False)
            fout.write('\n')
            fout.flush()

    # Write filtered and optionally sorted results
    if '.jsonl' in output_jsonl:
        log_file_deleted = output_jsonl.replace('.jsonl', '.deleted.jsonl')
    else:
        log_file_deleted = output_jsonl + '.deleted.jsonl'

    with open(log_file_deleted, 'w', encoding='utf-8') as fout:
        for result in deleted_lines:
            json.dump(result, fout, ensure_ascii=False)
            fout.write('\n')
            fout.flush()

    print(f"\nProcessing complete. Wrote {len(results)} results to {output_jsonl}")
    print(f"Found {found_trailing_invalid} trailing invalid characters in ASR results.")
    print(f"Filtered out {len(deleted_lines)} results with char_sim < {min_char_sim}")
    print(f"Wrote deleted {len(deleted_lines)} results to {log_file_deleted}")

if __name__ == "__main__":
    argh.dispatch_command(process_comparison)

"""
Usage examples:

First, run batch_asr_parallel.py.

# Basic usage
python batch_compare_asr_ref.py input.jsonl ref_dir output.jsonl

# Sort by similarity and custom filter
python batch_compare_asr_ref.py input.jsonl ref_dir output.jsonl --sort-by-similarity --min-char-sim=0.7

# Example with actual paths:
python batch\batch_compare_asr_ref.py .\OUTPUT-chirp3-all-wavs-aoede-asr.jsonl OUTPUT-chirp3-all-txts-aoede OUTPUT-chirp3-all-wavs-aoede-asrcompare.jsonl --sort-by-similarity
"""