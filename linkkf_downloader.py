import requests
from bs4 import BeautifulSoup
import os
import subprocess
import re

def sanitize_filename(name):
    """폴더 및 파일 이름으로 사용할 수 없는 문자를 제거하거나 대체합니다."""
    # Windows에서 허용되지 않는 문자: \ / : * ? " < > |
    # Linux/macOS에서 일반적으로 안전한 문자: /는 경로 구분자로 사용되므로 포함하지 않음
    invalid_chars = r'[\\/:*?"<>|]'
    return re.sub(invalid_chars, '', name) # 허용되지 않는 문자 제거

def download_video_and_subtitle(episode_title, video_id, episode_num, base_download_dir, referer_url):
    """
    지정된 에피소드 번호에 따라 비디오와 자막을 다운로드합니다.
    """
    # 폴더를 만들지 않고 base_download_dir에 직접 저장합니다.
    # 파일 이름은 '에피소드번호.mp4' 및 '에피소드번호.vtt' 형식으로 설정합니다.
    video_output_path = os.path.join(base_download_dir, f"{episode_num}.mp4")
    subtitle_output_path = os.path.join(base_download_dir, f"{episode_num}.vtt")

    # 비디오 URL 생성 (예: https://gg.myani.app/b2k38/m3u8/383518dvd1.m3u8)
    video_url = f"https://gg.myani.app/b2k38/m3u8/{video_id}dvd{episode_num}.m3u8"
    # 자막 URL 생성 (예: https://2.sub2.top/s/383518dvd1.vtt)
    subtitle_url = f"https://2.sub2.top/s/{video_id}dvd{episode_num}.vtt"

    print(f"\n--- 에피소드: {episode_title} ({episode_num}화) ---")
    print(f"비디오 URL: {video_url}")
    print(f"자막 URL: {subtitle_url}")

    # 1. 비디오 다운로드 (yt-dlp 사용)
    print(f"'{episode_title}' 비디오 다운로드 중...")
    try:
        yt_dlp_command = [
            "yt-dlp",
            "--referer", referer_url,
            "-o", video_output_path, # 출력 경로를 메인 폴더로 변경
            video_url
        ]
        # yt-dlp 진행 상황을 콘솔에 직접 출력하기 위해 capture_output=True 제거
        subprocess.run(yt_dlp_command, check=True, text=True) # text=True는 에러 메시지 캡처 시 필요
        print(f"'{episode_title}' 비디오 다운로드 완료: {video_output_path}")
    except subprocess.CalledProcessError as e:
        print(f"ERROR: '{episode_title}' 비디오 다운로드 실패. 오류: {e}")
        # capture_output=True가 없으므로 e.stdout/e.stderr는 비어 있을 수 있습니다.
        # yt-dlp의 실제 오류 메시지는 콘솔에 직접 출력됩니다.
        print("yt-dlp 설치 또는 경로 확인 필요. 또는 URL 접근 문제.")
        return # 비디오 다운로드 실패 시 자막 다운로드 시도 안 함

    # 2. 자막 다운로드 (requests 사용)
    print(f"'{episode_title}' 자막 다운로드 중...")
    try:
        headers = {"Referer": referer_url} # 자막도 Referer 필요할 수 있음
        response = requests.get(subtitle_url, headers=headers, stream=True)
        response.raise_for_status() # HTTP 오류가 발생하면 예외 발생

        with open(subtitle_output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        print(f"'{episode_title}' 자막 다운로드 완료: {subtitle_output_path}")

    except requests.exceptions.RequestException as e:
        print(f"ERROR: '{episode_title}' 자막 다운로드 실패. 오류: {e}")
        print("자막 URL 접근 문제 또는 파일이 존재하지 않을 수 있습니다.")


def main():
    user_url = input("애니메이션 페이지 URL을 입력하세요 (예: https://linkkf.net/ani/383518/): ")

    # URL에서 비디오 ID 추출 (예: 383518)
    match = re.search(r'ani/(\d+)/?$', user_url)
    if not match:
        print("ERROR: URL에서 애니메이션 ID를 찾을 수 없습니다. 올바른 형식의 URL을 입력해주세요.")
        return
    main_video_id = match.group(1)
    print(f"추출된 애니메이션 ID: {main_video_id}")

    # Referer URL은 linkkf.net 페이지 URL이 됩니다.
    referer_for_downloads = user_url

    # HTML 가져오기
    print(f"'{user_url}'에서 에피소드 목록을 가져오는 중...")
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36'}
        response = requests.get(user_url, headers=headers)
        response.raise_for_status() # HTTP 오류 시 예외 발생
        html_content = response.text
    except requests.exceptions.RequestException as e:
        print(f"ERROR: URL에 접근할 수 없습니다. 오류: {e}")
        return

    # BeautifulSoup으로 파싱
    soup = BeautifulSoup(html_content, 'html.parser')

    # .ewave-playlist-content UL 태그 찾기
    playlist_ul = soup.find('ul', class_='ewave-playlist-content')

    if not playlist_ul:
        print("ERROR: '.ewave-playlist-content' UL 태그를 찾을 수 없습니다. 페이지 구조가 변경되었거나 잘못된 URL입니다.")
        return

    # 비디오를 저장할 기본 디렉토리
    # 애니메이션 제목을 가져와 메인 폴더 이름으로 사용합니다.
    base_download_dir = sanitize_filename(soup.title.string.replace(' - Linkkf', '').strip() if soup.title else "Downloaded Anime")
    os.makedirs(base_download_dir, exist_ok=True)
    print(f"다운로드될 메인 폴더: {os.path.abspath(base_download_dir)}")

    # 에피소드 리스트 파싱 및 다운로드
    all_lis = playlist_ul.find_all('li')
    # 에피소드 번호를 1부터 시작하도록 역순 계산
    # 예를 들어 12화가 마지막이면 12, 11, ..., 1로 카운트
    # 실제 파일명은 1.mp4, 2.mp4 등으로 되도록 역순으로 순회하며 episode_num을 증가시킴
    # 이렇게 하면 가장 오래된 에피소드부터 순서대로 (1화, 2화, ...) 번호가 부여됩니다.
    
    # 에피소드가 실제로 존재하는지 확인하여 유효한 에피소드만 처리
    valid_episodes = []
    for li in all_lis:
        a_tag = li.find('a')
        if a_tag:
            valid_episodes.append(a_tag.get_text(strip=True))

    # 에피소드를 역순으로 처리하되, 파일명은 1화, 2화 순서로 부여
    # 웹사이트의 에피소드 목록이 보통 최신화가 위에 있으므로, 역순으로 돌면서 번호를 1부터 매깁니다.
    episode_counter = 1
    for episode_title in reversed(valid_episodes): # 유효한 에피소드 제목 리스트를 역순으로 순회
        download_video_and_subtitle(episode_title, main_video_id, episode_counter, base_download_dir, referer_for_downloads)
        episode_counter += 1

    print("\n모든 에피소드 다운로드 시도 완료.")

if __name__ == "__main__":
    main()
