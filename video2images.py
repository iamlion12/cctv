import os

def convert(video_folder, target_folder):
    """
    video_folder - string;
    target_folder - string;
    """
    try:
        video_list = os.listdir(video_folder)
    except Exception as e:
        print(e)

    try:
        cwd = os.getcwd()

        os.chdir(video_folder)
        os.system('for file in *; do find -name "$file" -type f | rename '+"'s/ /_/g'"+'; done')
    except Exception as e:
        print(e)

    os.chdir(cwd)
    os.system("bash video2images.sh {0} {1}".format(video_folder, target_folder))

if __name__ == "__main__":
    convert('video/', 'images/')
