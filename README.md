# AniManga-Ranker
### __Note: I did not code this, Copilot did 99.99% of the work, and I just told it what I wanted it to do. I do not claim to be a coder or programmer by any means, and all I did was test it to see if it worked.__

AniManga Ranker, coded in Python, helps users sort and order their completed anime/manga list from best to worst by using a modified binary search algorithm. 

### [Changelog](https://github.com/Joeytheduck1/AniManga-Ranker/wiki/Changelog)
## DISCLAIMER
Depending on how many anime/manga you have completed, it could easily take more than an hour or two. For reference, with 247 anime completed and assuming every choice takes 5 seconds, it will take roughly two hours to complete the program. __This is not for the faint of heart.__

<div style="display: flex; flex-wrap: wrap; gap: 10px;">
  <img src="https://i.ibb.co/RpNGgt5L/image.png" alt="AniManga Ranker Screenshot 1" width="800">
  <img src="https://i.ibb.co/HT9Wny3y/Screenshot-2025-04-17-195803.png" alt="AniManga Ranker Screenshot 2" width="400">
  <img src="https://i.ibb.co/20x8Nn5n/Screenshot-2025-04-17-195853.png" alt="AniManga Ranker Screenshot 3" width="400">
  <img src="https://i.ibb.co/Z17CvMtr/Screenshot-2025-04-19-170613.png" alt="AniManga Ranker Screenshot 4" width="800">
</div>

## Installation
You can find the latest release on the right. Or click on [this](https://github.com/Joeytheduck1/AniManga-Ranker/releases/latest). and download AniMangaRanker_(version)_.exe

Alternatively if you know what you are doing, you can clone the repository and install the necessary dependencies by running `pip install -r requirements.txt`


## How it works
__Note: Profile must be public for the program to work.__
1. Input your AniList username (No log in required)
2. Click either "Fetch Anime List" or "Fetch Manga List"
3. It gives you two choices of anime/manga
4. You pick which one is better (Don't worry if you're not sure, you can edit the list at any time by using the "Edit Sorted List" button.
5. Repeat steps 3-4 until all necessary comparisons are made to create the final list
6. The final result is printed in a pop-up window where every entry sorted is placed on separate lines

### A more detailed explanation of the sorting algorithm:
The AniList Api is used to get information about the user's completed anime/manga list. The list is stored in order of score, and media with the same score are shuffled with other media with the same score. The program starts from the highest-rated media and picks two pieces of media for the user to compare. After the user picks one of the two, they are put into a sorted list. The next entry is then compared to the midpoint of the sorted list. The user now compares the two anime presented, and if the new entry beats the midpoint, then it uses the midpoint as the new lower index and finds the new midpoint between the highest show on the sorted list and the new lower index. The same vice versa, where the mid point becomes the high index, and the new midpoint is calculated. This is repeated until the entry can be placed precisely where it belongs. The process repeats until there are no more unsorted anime.
