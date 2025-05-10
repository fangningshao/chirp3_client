import json
import argh
import os
from google.oauth2 import service_account
from google.cloud import speech_v1p1beta1 as speech
from google.cloud import storage

# 请替换为您的 Google Cloud Project ID
PROJECT_ID = ""

# 请替换为您的静态 token
STATIC_TOKEN = ""  # zf gmail 固定token

STORAGE_BUCKET = ""  # 请替换为您的 Google Cloud Storage Bucket 名称

# Read project_id and token from chirp3-keys.json in the same directory with the script:
try:
    keys_file = os.path.join(os.path.dirname(__file__), 'chirp3-keys.json')
    with open(keys_file, 'r') as f:
        keys = json.load(f)
        PROJECT_ID = keys['project_id']
        STATIC_TOKEN = keys['token']
        STORAGE_BUCKET = keys['storage_bucket']
    print("Loaded project_id and token from chirp3-keys.json")
except FileNotFoundError:
    print("chirp3-keys.json not found, using default values")
    pass

# Keep existing authentication setup
credentials = service_account.Credentials.from_service_account_file(
    os.path.join(os.path.dirname(__file__), 'gcs-keys.json'),
    scopes=['https://www.googleapis.com/auth/cloud-platform']
)

# Initialize clients with credentials
storage_client = storage.Client(
    credentials=credentials
)
client = speech.SpeechClient(credentials=credentials)

def upload_to_gcs(file_path: str, bucket_name: str) -> str:
    """Upload file to Google Cloud Storage and return the GCS URI."""
    try:
        bucket = storage_client.bucket(bucket_name)
        blob_name = os.path.basename(file_path)
        blob = bucket.blob(blob_name)
        blob.upload_from_filename(file_path)
        return f"gs://{bucket_name}/{blob_name}"
    except Exception as e:
        print(f"Error uploading to GCS: {e}")
        return None

def run_asr_long(speech_file, verbose=False, timeout=180, sample_rate=24000):
    """Execute speech recognition for long audio files."""
    try:
        if verbose:
            print(f"Processing file: {speech_file}")

        # Upload to GCS first
        gcs_uri = upload_to_gcs(speech_file, STORAGE_BUCKET)
        if not gcs_uri:
            raise Exception("Failed to upload to GCS")

        if verbose:
            print(f"Uploaded to GCS: {gcs_uri}")

        # Create the audio object with GCS URI
        audio = speech.RecognitionAudio(uri=gcs_uri)

        # Simplified recognition config without diarization
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=sample_rate,
            language_code="en-US",
            enable_automatic_punctuation=True,
            enable_word_confidence=True,
            profanity_filter=False,
            use_enhanced=True,
            model='phone_call',
            metadata=speech.RecognitionMetadata(
                interaction_type=speech.RecognitionMetadata.InteractionType.DISCUSSION,
                recording_device_type=speech.RecognitionMetadata.RecordingDeviceType.SMARTPHONE,
            )
        )

        operation = client.long_running_recognize(config=config, audio=audio)

        if verbose:
            print("Waiting for operation to complete...")

        response = operation.result(timeout=timeout)

        # Simplified results processing
        results_list = [result.alternatives[0].transcript for result in response.results]
        results_str = "\n".join(results_list)

        if verbose:
            print(f"Results for {speech_file}:", results_str)

        # Clean up GCS
        bucket = storage_client.bucket(STORAGE_BUCKET)
        blob = bucket.blob(os.path.basename(speech_file))
        blob.delete()

        return results_str

    except Exception as e:
        print(f"Error processing {speech_file}: {e}")
        return None


def batch(input_dir: str, output_file: str = "batch-asr-output.txt", verbose=False):
    """批量处理音频文件。
    Usage:
        python run_cloud_asr_batch.py batch input_dir output_file

    Args:
        input_dir: 包含音频文件的输入目录。
        output_file: 输出文本文件路径。
        verbose: 是否打印详细信息。
    """
    audio_files = [f for f in os.listdir(input_dir) if f.endswith('.wav')]

    with open(output_file, 'w', encoding='utf-8') as f:
        for audio_file in sorted(audio_files):
            file_path = os.path.join(input_dir, audio_file)
            result = run_asr_long(file_path, verbose)
            for line in result.splitlines():
                if line.strip():
                    f.write(f"{audio_file}\t{line.strip()}\n")
                    f.flush()


def single(input_file: str, output_file: str, verbose=False):
    """单个文件处理。
    Usage:
        python run_cloud_asr_batch.py single input.wav output.txt

    Args:
        input_file: 输入的音频文件路径。
        output_file: 输出文本文件路径。
        verbose: 是否打印详细信息。
    """
    result = run_asr_long(input_file, verbose)
    if verbose:
        print(f"Processing file: {input_file}")
    if result:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(result)
            f.flush()


if __name__ == "__main__":
    argh.dispatch_commands([single, batch])
