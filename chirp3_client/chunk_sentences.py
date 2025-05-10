import codecs
import argh
import re

def split_into_sentences(text):
    """
    Split text into sentences while preserving ellipsis.

    Args:
        text (str): Input text to split

    Returns:
        list: List of sentences
    """
    # Replace ellipsis temporarily
    text = text.replace('...', '<ELLIPSIS>')

    # Split on sentence endings followed by space or end of string
    sentences = re.split('([.!?](?:\s|$))', text)

    # Rejoin sentences with their endings and clean up
    sentences = [''.join(i) for i in zip(sentences[0::2], sentences[1::2] + [''] * (len(sentences[0::2]) - len(sentences[1::2])))]

    # Restore ellipsis and clean up sentences
    sentences = [s.replace('<ELLIPSIS>', '...').strip() for s in sentences if s.strip()]

    return sentences

def chunk_sentences(input_file, output_file, verbose=False, keep_topic=False, do_unique=True):
    """
    Chunks paragraphs into sentences while preserving the topic column.

    Args:
        input_file (str): Path to the input text file containing topic-paragraph pairs
        output_file (str): Path to the output text file to save chunked sentences
        verbose (bool): If True, print debug information
    """
    with codecs.open(output_file, 'w', encoding='utf-8') as fout:
        visited = set()
        for line in codecs.open(input_file, 'r', encoding='utf-8'):
            line = line.strip()
            if not line:
                continue

            parts = line.split('\t')
            if len(parts) != 2:
                if verbose:
                    print(f"Skipping invalid line: {line}")
                continue

            topic, content = parts
            topic = topic.split(':')[0]  # Remove any colons from topic

            sentences = split_into_sentences(content)

            for sentence in sentences:
                sent = sentence.strip()
                # Check for uniqueness
                if do_unique and sent in visited:
                    continue
                if sent:  # Only write non-empty sentences
                    visited.add(sent)
                    if keep_topic:
                        print(f"{topic}\t{sent}", file=fout)
                    else:
                        print(sent, file=fout)

            if verbose:
                print(f"Processed topic: {topic} - Split into {len(sentences)} sentences")

if __name__ == "__main__":
    argh.dispatch_command(chunk_sentences)
