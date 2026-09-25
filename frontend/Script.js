const homePage = document.getElementById("homePage");
const songPage = document.getElementById("songPage");
const libraryPage = document.getElementById("libraryPage");

const navHome = document.getElementById("navHome");
const navSearch = document.getElementById("navSearch");
const navLibrary = document.getElementById("navLibrary");

const searchInput = document.getElementById("searchInput");
const searchButton = document.getElementById("searchButton");
const songList = document.getElementById("songList");

const audioPlayer = document.getElementById("audioPlayer");
const playButton = document.getElementById("playButton");
const previousButton = document.getElementById("previousButton");
const nextButton = document.getElementById("nextButton");

const songCover = document.getElementById("songCover");
const songTitle = document.getElementById("songTitle");
const songArtist = document.getElementById("songArtist");
const currentTime = document.getElementById("currentTime");
const progressBar = document.getElementById("progressBar");
const duration = document.getElementById("duration");

const backButton = document.getElementById("backButton");

const showLyricsButton = document.getElementById("showLyricsButton");
const lyricsSection = document.getElementById("lyricsSection");
const lyricsContainer = document.getElementById("lyricsContainer");
const lyricsStatus = document.getElementById("lyricsStatus");

const libraryList = document.getElementById("libraryList");

let syncedLyrics = [];
let currentSongs = [];
let currentSongIndex = 0;

function showPage(page) {
    homePage.hidden = true;
    songPage.hidden = true;
    libraryPage.hidden = true;

    page.hidden = false;
}

showPage(homePage);

// Lyrics panel starts closed.
lyricsSection.hidden = true;

navHome.addEventListener("click", () => {
    showPage(homePage);
});

navSearch.addEventListener("click", () => {
    showPage(homePage);
    searchInput.focus();
});

navLibrary.addEventListener("click", () => {
    showPage(libraryPage);
});

playButton.addEventListener("click", async () => {
    if (audioPlayer.paused) {
        try {
            await audioPlayer.play();
            playButton.textContent = "⏸";
        } catch (error) {
            console.error("Gagal memutar audio:", error);
        }
    } else {
        audioPlayer.pause();
        playButton.textContent = "▶";
    }
});

audioPlayer.addEventListener("ended", () => {
    playButton.textContent = "▶";
});

backButton.addEventListener("click", () => {
    showPage(homePage);
});

searchButton.addEventListener("click", searchMusic);

async function searchMusic() {
    const query = searchInput.value.trim();

    if (!query) {
        return;
    }

    try {
        const response = await fetch(
            `/api/search?q=${encodeURIComponent(query)}`
        );

        const data = await response.json();

        currentSongs = data.results || [];
        currentSongIndex = 0;

        songList.innerHTML = "";

        currentSongs.forEach(song => {
            const songItem = document.createElement("div");

            songItem.classList.add("songItem");

            songItem.innerHTML = `
                <img src="${song.image}" alt="${song.name}">
                <div class="songItemInfo">
                    <h3>${song.name}</h3>
                    <p>${song.artist_name}</p>
                </div>
            `;

            songItem.addEventListener("click", () => {
                currentSongIndex = currentSongs.indexOf(song);
                openSong(song);
            });

            songList.appendChild(songItem);
        });

    } catch (error) {
        console.error("Search gagal:", error);
    }
}

function openSong(song) {
    songTitle.textContent = song.name;
    songArtist.textContent = song.artist_name;
    songCover.src = song.image;

    audioPlayer.src = song.audio;
    playButton.textContent = "▶";

    // Reset lyrics panel for the new song.
    lyricsSection.hidden = true;
    lyricsContainer.innerHTML = "";
    lyricsStatus.textContent = "";

    showPage(songPage);
}

previousButton.addEventListener("click", () => {
    if (currentSongIndex > 0) {
        currentSongIndex--;

        openSong(currentSongs[currentSongIndex]);
    }
});

nextButton.addEventListener("click", () => {
    if (currentSongIndex < currentSongs.length - 1) {
        currentSongIndex++;

        openSong(currentSongs[currentSongIndex]);
    }
});

audioPlayer.addEventListener("loadedmetadata", () => {
    duration.textContent = formatTime(audioPlayer.duration);
    progressBar.max = audioPlayer.duration;
});

audioPlayer.addEventListener("timeupdate", () => {

    currentTime.textContent =
        formatTime(audioPlayer.currentTime);

    progressBar.value =
        audioPlayer.currentTime;

    updateLyrics();
});

function updateLyrics() {

    if (!syncedLyrics.length) {
        return;
    }

    const currentTime = audioPlayer.currentTime;

    let activeIndex = -1;

    for (let i = 0; i < syncedLyrics.length; i++) {

        if (currentTime >= syncedLyrics[i].time) {
            activeIndex = i;
        } else {
            break;
        }
    }

    if (activeIndex === -1) {
        return;
    }

    const lyricElements =
        lyricsContainer.querySelectorAll(".lyricLine");

    lyricElements.forEach((element, index) => {

        element.classList.remove("active");
        element.classList.remove("passed");

        if (index < activeIndex) {
            element.classList.add("passed");
        }

    });

    const activeLine = lyricElements[activeIndex];

    if (activeLine) {

        activeLine.classList.add("active");

        activeLine.scrollIntoView({
            behavior: "smooth",
            block: "center"
        });
    }
}

progressBar.addEventListener("input", () => {
    audioPlayer.currentTime = progressBar.value;
});

function formatTime(seconds) {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = Math.floor(seconds % 60);

    return `${String(minutes).padStart(2, "0")}:${String(remainingSeconds).padStart(2, "0")}`;
}


// ==========================================
// LYRICS
// ==========================================

showLyricsButton.addEventListener("click", async () => {
    lyricsSection.hidden = !lyricsSection.hidden;

    if (lyricsSection.hidden) {
        return;
    }

    // Already fetched for this song — don't re-fetch.
    if (lyricsContainer.childElementCount > 0) {
        return;
    }

    lyricsStatus.textContent = "Memuat lirik...";
    lyricsContainer.innerHTML = "";

    try {
        const response = await fetch(
            `/api/lyrics?title=${encodeURIComponent(songTitle.textContent)}&artist=${encodeURIComponent(songArtist.textContent)}`
        );

        const data = await response.json();

        if (!data.lyrics && !data.syncedLyrics) {
            lyricsStatus.textContent = "Lirik tidak ditemukan.";
            return;
        }

        lyricsStatus.textContent = "";

        if (data.syncedLyrics) {

            renderSyncedLyrics(data.syncedLyrics);

        } else {

            lyricsContainer.innerHTML = "";

            data.lyrics.split("\n").forEach(line => {

                const p = document.createElement("p");

                p.className = "lyricLine";
                p.textContent = line || "\u00A0";

                lyricsContainer.appendChild(p);
            });
        }

    } catch (error) {
        console.error("Gagal mengambil lirik:", error);
        lyricsStatus.textContent = "Gagal mengambil lirik.";
    }
});

function parseLRC(lrc) {

    const lines = [];

    lrc.split("\n").forEach(line => {

        const match = line.match(
            /^\[(\d+):(\d+(?:\.\d+)?)\]\s*(.*)$/
        );

        if (!match) {
            return;
        }

        const minutes = Number(match[1]);
        const seconds = Number(match[2]);

        lines.push({
            time: minutes * 60 + seconds,
            text: match[3]
        });
    });

    return lines.sort((a, b) => a.time - b.time);
}

function renderSyncedLyrics(lrc) {

    lyricsContainer.innerHTML = "";

    syncedLyrics = parseLRC(lrc);

    syncedLyrics.forEach((line, index) => {

        const p = document.createElement("p");

        p.className = "lyricLine";
        p.textContent = line.text;

        p.dataset.index = index;

        lyricsContainer.appendChild(p);
    });
}
