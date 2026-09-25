/**
 * sagaData.js - Canon One Piece Storyline Taxonomy & Metadata.
 * Encapsulates the entire saga breakdown with volume/chapter ranges, Japanese names,
 * thematic colors, and high-impact banner paths.
 */

export const CANON_SAGAS = [
  {
    id: "east-blue",
    name: "East Blue Saga",
    japaneseName: "東の海（イーストブルー）編",
    volumeRange: [1, 12],
    chapterRange: [1, 100],
    bannerUrl: "assets/arcs/east-blue.webp",
    themeColor: "#38bdf8",
    badgeColor: "bg-sky-500/20 text-sky-300 border-sky-500/30",
    description: "Luffy sets sail into the East Blue to gather his first crewmates — Zoro, Nami, Usopp, and Sanji — and earn his first pirate bounty on the way to the Grand Line.",
    arcs: ["Romance Dawn", "Orange Town", "Syrup Village", "Baratie", "Arlong Park", "Loguetown"]
  },
  {
    id: "arabasta",
    name: "Arabasta Saga",
    japaneseName: "アラバスタ編",
    volumeRange: [12, 24],
    chapterRange: [101, 217],
    bannerUrl: "assets/arcs/alabasta.webp",
    themeColor: "#fbbf24",
    badgeColor: "bg-amber-500/20 text-amber-300 border-amber-500/30",
    description: "The Straw Hats enter the Grand Line alongside Princess Vivi of Arabasta to foil the sinister plot of Warlord Crocodile and Baroque Works.",
    arcs: ["Reverse Mountain", "Whiskey Peak", "Little Garden", "Drum Island", "Arabasta"]
  },
  {
    id: "sky-island",
    name: "Sky Island Saga",
    japaneseName: "空島編",
    volumeRange: [24, 32],
    chapterRange: [218, 303],
    bannerUrl: "assets/arcs/skypiea.webp",
    themeColor: "#a78bfa",
    badgeColor: "bg-purple-500/20 text-purple-300 border-purple-500/30",
    description: "Riding the Knock Up Stream 10,000 meters into the clouds, the crew discovers Skypiea and clashes with the lightning god Enel.",
    arcs: ["Jaya", "Skypiea"]
  },
  {
    id: "water-7",
    name: "Water 7 Saga",
    japaneseName: "ウォーターセブン編",
    volumeRange: [32, 46],
    chapterRange: [304, 441],
    bannerUrl: "assets/arcs/water-7.webp",
    themeColor: "#3b82f6",
    badgeColor: "bg-blue-500/20 text-blue-300 border-blue-500/30",
    description: "Betrayal, heartbreak, and government espionage collide in the City of Water, forcing the Straw Hats to declare war on the World Government at Enies Lobby.",
    arcs: ["Long Ring Long Land", "Water 7", "Enies Lobby", "Post-Enies Lobby"]
  },
  {
    id: "thriller-bark",
    name: "Thriller Bark Saga",
    japaneseName: "スリラーバーク編",
    volumeRange: [46, 50],
    chapterRange: [442, 489],
    bannerUrl: "assets/arcs/water-7.webp",
    themeColor: "#c084fc",
    badgeColor: "bg-fuchsia-500/20 text-fuchsia-300 border-fuchsia-500/30",
    description: "Trapped in the Florian Triangle, the crew meets the skeleton musician Brook and battles the shadow-stealing Warlord Gecko Moria.",
    arcs: ["Thriller Bark"]
  },
  {
    id: "summit-war",
    name: "Summit War Saga",
    japaneseName: "頂上戦争編",
    volumeRange: [50, 61],
    chapterRange: [490, 597],
    bannerUrl: "assets/arcs/summit-war.webp",
    themeColor: "#ef4444",
    badgeColor: "bg-red-500/20 text-red-300 border-red-500/30",
    description: "Separated across the world, Luffy infiltrates Impel Down and rushes to Marineford to rescue his brother Portgas D. Ace in the war that reshaped the world.",
    arcs: ["Sabaody Archipelago", "Amazon Lily", "Impel Down", "Marineford", "Post-War"]
  },
  {
    id: "fish-man-island",
    name: "Fish-Man Island Saga",
    japaneseName: "魚人島編",
    volumeRange: [61, 66],
    chapterRange: [598, 653],
    bannerUrl: "assets/arcs/east-blue.webp",
    themeColor: "#2dd4bf",
    badgeColor: "bg-teal-500/20 text-teal-300 border-teal-500/30",
    description: "Reuniting after two years of intense training, the Straw Hats descend 10,000 meters beneath the sea to Fish-Man Island.",
    arcs: ["Return to Sabaody", "Fish-Man Island"]
  },
  {
    id: "dressrosa",
    name: "Dressrosa Saga",
    japaneseName: "ドレスローザ編",
    volumeRange: [66, 80],
    chapterRange: [654, 801],
    bannerUrl: "assets/arcs/alabasta.webp",
    themeColor: "#f43f5e",
    badgeColor: "bg-rose-500/20 text-rose-300 border-rose-500/30",
    description: "Forming a pirate alliance with Trafalgar Law, Luffy challenges Donquixote Doflamingo to liberate the puppet kingdom of Dressrosa.",
    arcs: ["Punk Hazard", "Dressrosa"]
  },
  {
    id: "four-emperors",
    name: "Whole Cake Island Saga",
    japaneseName: "ホールケーキアイランド編",
    volumeRange: [80, 90],
    chapterRange: [802, 908],
    bannerUrl: "assets/arcs/skypiea.webp",
    themeColor: "#f472b6",
    badgeColor: "bg-pink-500/20 text-pink-300 border-pink-500/30",
    description: "Luffy infiltrates Emperor Big Mom's sweet archipelago territory to rescue Sanji from an arranged political wedding.",
    arcs: ["Zou", "Whole Cake Island", "Levely"]
  },
  {
    id: "wano",
    name: "Wano Country Saga",
    japaneseName: "ワノ国編",
    volumeRange: [90, 105],
    chapterRange: [909, 1057],
    bannerUrl: "assets/arcs/wano.webp",
    themeColor: "#8b5cf6",
    badgeColor: "bg-violet-500/20 text-violet-300 border-violet-500/30",
    description: "In the secluded samurai nation of Wano, the Ninja-Pirate-Mink-Samurai Alliance launches an epic raid on Onigashima to overthrow Emperors Kaido and Big Mom.",
    arcs: ["Wano Country"]
  },
  {
    id: "final-saga",
    name: "Final Saga",
    japaneseName: "最終章",
    volumeRange: [105, 115],
    chapterRange: [1058, 1200],
    bannerUrl: "assets/arcs/final-saga.webp",
    themeColor: "#e11d48",
    badgeColor: "bg-red-500/20 text-red-300 border-red-500/30",
    description: "The Straw Hats arrive at the futuristic island of Egghead and onward toward Elbaf, meeting Dr. Vegapunk, the Sun God Nika revelations, and the ancient secrets shaking the world.",
    arcs: ["Egghead", "Elbaf"]
  }
];

export function getSagaById(sagaId) {
  return CANON_SAGAS.find(s => s.id === sagaId) || CANON_SAGAS[0];
}

export function getSagaForVolume(volNum) {
  const num = Number(volNum);
  const found = CANON_SAGAS.find(s => num >= s.volumeRange[0] && num <= s.volumeRange[1]);
  return found || CANON_SAGAS[CANON_SAGAS.length - 1];
}
