import json
import argh
import os
from google.oauth2 import service_account
from google.cloud import speech_v1p1beta1 as speech
from google.auth.credentials import Credentials
from google.cloud import storage
from google.api_core.client_options import ClientOptions


GOOGLE_APPLICATION_CREDENTIALS="gcs-keys.json"
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = GOOGLE_APPLICATION_CREDENTIALS


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

credentials = service_account.Credentials.from_service_account_file(
    os.path.join(os.path.dirname(__file__), 'gcs-keys.json'),
    scopes=['https://www.googleapis.com/auth/cloud-platform']
)

# client = speech.SpeechClient(
#     client_options=ClientOptions(api_key=STATIC_TOKEN)
# )
client = speech.SpeechClient(
    credentials=credentials,
)


def merge_consecutive_speakers(words_info, add_speaker_tag=False):
    current_speaker = None
    current_sentence = []
    result = []

    for i, word_info in enumerate(words_info):
        if current_speaker is None:
            current_speaker = word_info.speaker_tag
            current_sentence.append(word_info.word)
            continue

        if word_info.speaker_tag != current_speaker:
            formatted = format_sentence(current_sentence)
            if add_speaker_tag:
                formatted = f"Speaker {current_speaker}: {formatted}"
            else:
                formatted = f"{formatted}"
            result.append(formatted)
            current_speaker = word_info.speaker_tag
            current_sentence = [word_info.word]
        else:
            current_sentence.append(word_info.word)

    if current_sentence:
        formatted = format_sentence(current_sentence)
        if add_speaker_tag:
            formatted = f"Speaker {current_speaker}: {formatted}"
        else:
            formatted = f"{formatted}"
        result.append(formatted)

    return "\n".join(result)

def format_sentence(words):
    """处理标点符号格式"""
    sentence = " ".join(words)
    replacements = [
        (" ,", ","), (" .", "."), (" ?", "?"), (" !", "!"),
        (" '", "'"), (" ;", ";"), (" :", ":")]
    for old, new in replacements:
        sentence = sentence.replace(old, new)
    return sentence

def run_asr(speech_file, verbose=False, add_speaker_tag=False):
    """执行语音识别并进行说话人分离。

    Args:
        speech_file: 输入的音频文件路径。
        verbose: 是否打印详细信息。
    """
    try:
        with open(speech_file, "rb") as audio_file:
            content = audio_file.read()

        audio = speech.RecognitionAudio(content=content)

        diarization_config = speech.SpeakerDiarizationConfig(
            enable_speaker_diarization=True,
            min_speaker_count=2,
            max_speaker_count=10,
        )

        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=24000,
            language_code="en-US",
            diarization_config=diarization_config,
            enable_automatic_punctuation=True,
            enable_word_confidence=True,
            profanity_filter=False,  # 不过滤任何词
            use_enhanced=True,  # 使用增强模型
            model='phone_call',  # 使用适合对话的模型
            # 如果需要更多细节，可以添加
            metadata=speech.RecognitionMetadata(
                interaction_type=speech.RecognitionMetadata.InteractionType.DISCUSSION,
                recording_device_type=speech.RecognitionMetadata.RecordingDeviceType.SMARTPHONE,
            )
        )

        if verbose:
            print(f"Processing file: {speech_file}")

        response = client.recognize(config=config, audio=audio)
        result = response.results[-1]
        words_info = result.alternatives[0].words
        results_str = merge_consecutive_speakers(words_info, add_speaker_tag=add_speaker_tag)
        if verbose:
            print(f"Results for {speech_file}:", results_str)

        return results_str

    except Exception as e:
        print(f"Error processing {speech_file}: {e}")
        return None


# 使用相同的认证初始化两个客户端
storage_client = storage.Client(
    project=PROJECT_ID,
    credentials=credentials
)
# Create bucket if it doesn't exist
bucket = storage_client.bucket(STORAGE_BUCKET)

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

def run_asr_long(speech_file, verbose=False, add_speaker_tag=False, timeout=180):
    """执行语音识别并进行说话人分离。支持长音频文件。"""
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

        diarization_config = speech.SpeakerDiarizationConfig(
            enable_speaker_diarization=True,
            min_speaker_count=2,
            max_speaker_count=2,
        )

        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=24000,
            language_code="en-US",
            diarization_config=diarization_config,
            enable_automatic_punctuation=True,
        )

        # Use long_running_recognize with GCS URI
        operation = client.long_running_recognize(config=config, audio=audio)

        if verbose:
            print("Waiting for operation to complete...")

        response = operation.result(timeout=timeout)

        # Process results
        result = response.results[-1]
        words_info = result.alternatives[0].words
        results_str = merge_consecutive_speakers(words_info, add_speaker_tag=add_speaker_tag)

        if verbose:
            print(f"Results for {speech_file}:", results_str)

        # Clean up GCS
        bucket = storage_client.bucket(STORAGE_BUCKET)
        # Create folder inside the bucket named chirp3_test
        blob = bucket.blob(os.path.basename(speech_file))
        blob.delete()

        return results_str

    except Exception as e:
        print(f"Error processing {speech_file}: {e}")
        return None



def batch(input_dir: str, output_file: str = "batch-asr-output.txt", verbose=False, add_speaker_tag=False):
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
            result = run_asr_long(file_path, verbose, add_speaker_tag=add_speaker_tag)
            for line in result.splitlines():
                if line.strip():
                    f.write(f"{audio_file}\t{line.strip()}\n")
            # if result:
            #     f.write(f"{audio_file}\t{result}\n")


def single(input_file: str, output_file: str, verbose=False, add_speaker_tag=False):
    """单个文件处理。
    Usage:
        python run_cloud_asr_batch.py single input.wav output.txt

    Args:
        input_file: 输入的音频文件路径。
        output_file: 输出文本文件路径。
        verbose: 是否打印详细信息。
    """
    result = run_asr_long(input_file, verbose, add_speaker_tag=add_speaker_tag)
    if verbose:
        print(f"Processing file: {input_file}")
    if result:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(result)


if __name__ == "__main__":
    argh.dispatch_commands([single, batch])
