# AniManga-Ranker
### __Note: I did not code this, Copilot did 99.99% of the work, and I just told it what I wanted it to do. I do not claim to be a coder or programmer by any means, and all I did was test it to see if it worked.__

AniManga Ranker, coded in Python, helps users sort and order their completed anime/manga list from best to worst by using a modified binary search algorithm. 

### [Changelog](https://github.com/Joeytheduck1/AniManga-Ranker/wiki/Changelog) | [Planned Features](https://github.com/Joeytheduck1/AniManga-Ranker/wiki/Planned-Features)
## DISCLAIMER
Depending on how many anime/manga you have completed, it could easily take more than an hour or two. For reference, with 247 anime completed and assuming every choice takes 5 seconds, it will take roughly two hours to complete the program. __This is not for the faint of heart.__

<div style="display: flex; flex-wrap: wrap; gap: 10px;">
  <img src="https://joeytheduck1.github.io/AniManga-Ranker/" alt="AniManga Ranker Screenshot 1" width="800">
</div>

## How to use
It's hosted on this website just click this link https://joeytheduck1.github.io/AniManga-Ranker/

## How it works
__Note: Profile must be public for the program to work.__
1. Input your AniList username (No login required)
2. Select what lists you want the program to pull from and whether or not you want to include images
3. Click either "Fetch Anime List" or "Fetch Manga List"
4. It gives you two choices of anime/manga
5. You pick which one is better (Don't worry if you're not sure, you can edit the list at any time by using the "Edit Sorted List" button.
6. Repeat steps 4-5 until all necessary comparisons are made to create the final list
7. The final result is printed in a pop-up window where every entry sorted is placed on separate lines

### A more detailed explanation of the sorting algorithm:
The AniList Api is used to get information about the user's completed anime/manga list. The list is stored in order of score, and media with the same score are shuffled with other media with the same score. The program starts from the highest-rated media and picks two pieces of media for the user to compare. After the user picks one of the two, they are put into a sorted list. The next entry is then compared to the midpoint of the sorted list. The user now compares the two anime presented, and if the new entry beats the midpoint, then it uses the midpoint as the new lower index and finds the new midpoint between the highest show on the sorted list and the new lower index. The same vice versa, where the mid point becomes the high index, and the new midpoint is calculated. This is repeated until the entry can be placed precisely where it belongs. The process repeats until there are no more unsorted anime. The algorithm has been updated and works basically the same but it assumes you are inserting stuff near the bottom because the unsorted list is actually pre sorted by score so it should reduce the number of comparisons.
