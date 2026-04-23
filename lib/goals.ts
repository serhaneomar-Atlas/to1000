// ============================================================
// To1000.com — Données et logique métier CR7
// Sources: ESPN, Transfermarkt, Wikipedia (vérifié avril 2026)
// ============================================================

export interface ClubStats {
  club: string;
  logo: string;
  country: string;
  years: string;
  appearances: number;
  goals: number;
  color: string;
}

export interface CompetitionStats {
  competition: string;
  goals: number;
  appearances: number;
}

export interface SeasonStats {
  season: string;
  club: string;
  goals: number;
}

export interface MilestoneGoal {
  number: number;
  date: string;
  opponent: string;
  competition: string;
  club: string;
  description: string;
}

// ── Données actuelles (à mettre à jour après chaque match) ──
export const CURRENT_GOALS = 967;
export const TARGET_GOALS = 1000;
export const GOALS_REMAINING = TARGET_GOALS - CURRENT_GOALS;
export const LAST_UPDATED = "2026-04-03";

// ── Rythme de buts récent ──
// 2025: 41 buts en 46 matchs ≈ 0.89 buts/match
// 2025/2026 saison: 23 buts en 23 matchs ≈ 1.0 buts/match
// Estimation conservatrice: ~0.85 buts/match, ~2 matchs/semaine
export const GOALS_PER_DAY = 0.85 * 2 / 7; // ~0.243 buts/jour
export const ESTIMATED_DAYS = Math.ceil(GOALS_REMAINING / GOALS_PER_DAY);

// Date estimée d'atteinte des 1000 buts
export const ESTIMATED_DATE = new Date();
ESTIMATED_DATE.setDate(ESTIMATED_DATE.getDate() + ESTIMATED_DAYS);

// ── Stats par club ──
export const CLUB_STATS: ClubStats[] = [
  {
    club: "Sporting CP",
    logo: "/clubs/sporting.svg",
    country: "Portugal",
    years: "2002-2003",
    appearances: 31,
    goals: 5,
    color: "#00543D",
  },
  {
    club: "Manchester United",
    logo: "/clubs/manutd.svg",
    country: "Angleterre",
    years: "2003-2009, 2021-2022",
    appearances: 346,
    goals: 144,
    color: "#DA291C",
  },
  {
    club: "Real Madrid",
    logo: "/clubs/realmadrid.svg",
    country: "Espagne",
    years: "2009-2018",
    appearances: 438,
    goals: 450,
    color: "#FEBE10",
  },
  {
    club: "Juventus",
    logo: "/clubs/juventus.svg",
    country: "Italie",
    years: "2018-2021",
    appearances: 134,
    goals: 101,
    color: "#000000",
  },
  {
    club: "Al Nassr",
    logo: "/clubs/alnassr.svg",
    country: "Arabie Saoudite",
    years: "2023-présent",
    appearances: 124,
    goals: 124,
    color: "#FFC425",
  },
  {
    club: "Portugal",
    logo: "/clubs/portugal.svg",
    country: "Sélection",
    years: "2003-présent",
    appearances: 217,
    goals: 143,
    color: "#006847",
  },
];

// ── Stats par compétition ──
export const COMPETITION_STATS: CompetitionStats[] = [
  { competition: "Ligues nationales", goals: 512, appearances: 680 },
  { competition: "Ligue des Champions", goals: 141, appearances: 183 },
  { competition: "Sélection (compétitif)", goals: 133, appearances: 200 },
  { competition: "Coupes nationales", goals: 48, appearances: 72 },
  { competition: "Supercoupe / Coupe du Monde des Clubs", goals: 21, appearances: 30 },
  { competition: "Sélection (amical)", goals: 10, appearances: 17 },
  { competition: "Qualifications", goals: 52, appearances: 80 },
  { competition: "Saudi Pro League", goals: 50, appearances: 55 },
];

// ── Buts marquants / Milestones ──
export const MILESTONE_GOALS: MilestoneGoal[] = [
  {
    number: 1,
    date: "2002-10-07",
    opponent: "Moreirense",
    competition: "Primeira Liga",
    club: "Sporting CP",
    description: "Premier but en carrière professionnelle à 17 ans",
  },
  {
    number: 100,
    date: "2007-10-17",
    opponent: "Dynamo Kiev",
    competition: "Ligue des Champions",
    club: "Manchester United",
    description: "100e but — déjà une légende en devenir",
  },
  {
    number: 200,
    date: "2010-10-23",
    opponent: "Racing Santander",
    competition: "La Liga",
    club: "Real Madrid",
    description: "200e but — la machine Real Madrid est lancée",
  },
  {
    number: 300,
    date: "2013-01-06",
    opponent: "Real Sociedad",
    competition: "La Liga",
    club: "Real Madrid",
    description: "300e but en seulement 3 ans supplémentaires",
  },
  {
    number: 400,
    date: "2014-12-20",
    opponent: "Ludogorets",
    competition: "La Liga",
    club: "Real Madrid",
    description: "400e but — record sur record",
  },
  {
    number: 500,
    date: "2017-01-29",
    opponent: "Betis Séville",
    competition: "La Liga",
    club: "Real Madrid",
    description: "500e but — demi-millénaire historique",
  },
  {
    number: 600,
    date: "2018-10-20",
    opponent: "Udinese",
    competition: "Serie A",
    club: "Juventus",
    description: "600e but — la conquête de l'Italie",
  },
  {
    number: 700,
    date: "2019-10-14",
    opponent: "Ukraine",
    competition: "Qualifications Euro",
    club: "Portugal",
    description: "700e but sous les couleurs du Portugal",
  },
  {
    number: 800,
    date: "2022-11-24",
    opponent: "Ghana",
    competition: "Coupe du Monde",
    club: "Portugal",
    description: "800e but en Coupe du Monde — historique",
  },
  {
    number: 900,
    date: "2024-09-05",
    opponent: "Croatie",
    competition: "Ligue des Nations",
    club: "Portugal",
    description: "900e but — plus que 100 pour la légende absolue",
  },
  {
    number: 950,
    date: "2025-09-20",
    opponent: "Al Ahli",
    competition: "Saudi Pro League",
    club: "Al Nassr",
    description: "950e but — le 1000e est en vue",
  },
];

// ── Fonctions utilitaires ──

export function calculateCountdown() {
  const now = new Date();
  const target = new Date(ESTIMATED_DATE);
  const diff = target.getTime() - now.getTime();

  if (diff <= 0) {
    return { days: 0, hours: 0, minutes: 0, seconds: 0 };
  }

  return {
    days: Math.floor(diff / (1000 * 60 * 60 * 24)),
    hours: Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60)),
    minutes: Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60)),
    seconds: Math.floor((diff % (1000 * 60)) / 1000),
  };
}

export function getProgressPercentage() {
  return (CURRENT_GOALS / TARGET_GOALS) * 100;
}

export function formatNumber(n: number): string {
  return n.toLocaleString("fr-FR");
}

export function getGoalsByType(): { club: number; international: number } {
  const international = CLUB_STATS.find((s) => s.club === "Portugal")?.goals || 0;
  const club = CURRENT_GOALS - international;
  return { club, international };
}
