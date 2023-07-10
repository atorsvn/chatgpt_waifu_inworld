import os
import json
import datetime
import subprocess
import tempfile
from inworld_python import inworld_chat

class AvatarRig:
    def __init__(self, config_path):
        with open(config_path) as config_file:
            config = json.load(config_file)
        self.inworld_key = config['inworld_key']
        self.inworld_secret = config['inworld_secret']
        self.inworld_scene = config['inworld_scene']
        self.avatar_video_path = config['avatar_video_path']
        self.user_name = None
        self.objects_list = None
        self.chat_app = inworld_chat.InWorldChat(self.inworld_key, self.inworld_secret, self.inworld_scene)

    def create_srt_from_chat(self, objects_list, chars_per_second=15):
        srt_string = ''
        start_time = datetime.timedelta()

        for i, obj in enumerate(objects_list, start=1):
            text = obj['text']
            end_time = start_time + datetime.timedelta(seconds=len(text) / chars_per_second)

            # Ensure timestamps are in 'HH:MM:SS,mmm' format
            start_time_str = '{:02}:{:02}:{:02},{:03}'.format(int(start_time.total_seconds() // 3600),
                                                            int((start_time.total_seconds() % 3600) // 60),
                                                            int(start_time.total_seconds() % 60),
                                                            start_time.microseconds // 1000)
            end_time_str = '{:02}:{:02}:{:02},{:03}'.format(int(end_time.total_seconds() // 3600),
                                                            int((end_time.total_seconds() % 3600) // 60),
                                                            int(end_time.total_seconds() % 60),
                                                            end_time.microseconds // 1000)
            srt_string += f"{i}\n{start_time_str} --> {end_time_str}\n{text}\n\n"
            start_time = end_time

        return srt_string


    def chat_query(self, query, user_name, channel_id, user_id):
        self.user_name = user_name
        out = self.chat_app.chat(query, user_name, channel_id, user_id)
        self.objects_list = json.loads(out)
        srt_content = self.create_srt_from_chat(self.objects_list)

        with open("subtitles.srt", "w") as file:
            file.write(srt_content)

    def create_avatar_video(self, output_file_path='output.mp4', gif_output_folder='result'):
        self.cleanup()

        # Create temporary file
        temp_srt_file = tempfile.NamedTemporaryFile(delete=False, suffix=".srt")
        temp_srt_file_path = temp_srt_file.name.replace("\\", "\\\\")

        # Write srt content into the temporary file
        temp_srt_file.write(self.create_srt_from_chat(self.objects_list).encode())
        temp_srt_file.close()

        # Find the total duration of the text based on the end time of the last subtitle
        with open(temp_srt_file_path, 'r') as file:
            last_line = file.readlines()[-3]
        total_duration = int(last_line.split("-->")[1].strip().split(":")[0]) * 3600 + \
                        int(last_line.split("-->")[1].strip().split(":")[1]) * 60 + \
                        int(last_line.split("-->")[1].strip().split(":")[2].split(",")[0])

        # Calculate the duration of the avatar video
        result = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                "-of", "default=noprint_wrappers=1:nokey=1", self.avatar_video_path],
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        avatar_duration = int(float(result.stdout))

        # Calculate how many times we need to loop the avatar video
        loop_count = total_duration // avatar_duration + 1

        # Use ffmpeg to loop the video and add the .srt file
        subprocess.run(['ffmpeg', '-stream_loop', str(loop_count), '-i', self.avatar_video_path, '-vf', f'subtitles=subtitles.srt', output_file_path])

        # Create a folder for the resulting GIF if it doesn't exist
        if not os.path.exists(gif_output_folder):
            os.makedirs(gif_output_folder)

        # Generate the output file path based on the user name and current time
        current_time = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        gif_output_path = os.path.join(gif_output_folder, f"{self.user_name}_{current_time}.gif")

        # Convert the video to GIF and save it to the specified folder
        subprocess.run(['ffmpeg', '-i', output_file_path, gif_output_path])

        # Delete the temporary .srt file
        os.unlink(temp_srt_file_path)

        # Concatenate chat text and save along with the gif file path
        chat_text = ' '.join([obj['text'] for obj in self.objects_list])
        result = json.dumps({
            'chat_text': chat_text,
            'gif_file': gif_output_path
        })

        return result

    def cleanup(self):
        # Delete the output.mp4 file
        if os.path.exists("output.mp4"):
            os.remove("output.mp4")

