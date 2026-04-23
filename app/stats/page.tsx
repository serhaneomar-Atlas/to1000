import type { Metadata } from "next";
import StatsCard from "@/components/StatsCard";
import {
  CURRENT_GOALS,
  TARGET_GOALS,
  GOALS_REMAINING,
  CLUB_STATS,
  COMPETITION_STATS,
  getGoalsByType,
} from "@/lib/goals";

export const metadata: Metadata = {
  title: "Statistiques CR7",
  description: "Toutes les statistiques de Cristiano Ronaldo : buts par club, par compétition, records et plus.",
};

function ClubCard({ club }: { club: typeof CLUB_STATS[0] }) {
  const percentage = ((club.goals / CURRENT_GOALS) * 100).toFixed(1);
  const ratio = (club.goals / club.appearances).toFixed(2);

  return (
    <div className="bg-white/[0.02] border border-white/5 rounded-2xl p-5 sm:p-6 hover:border-white/15 transition-all group">
      <div className="flex items-center gap-3 mb-4">
        <div
          className="w-10 h-10 sm:w-12 sm:h-12 rounded-full flex items-center justify-center text-lg font-bold text-white"
          style={{ backgroundColor: club.color }}
        >
          {club.club[0]}
        </div>
        <div>
          <h3 className="font-bold text-white/90 text-sm sm:text-base">{club.club}</h3>
          <p className="text-xs text-white/30">{club.years}</p>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-3">
        <div>
          <p className="text-xl sm:text-2xl font-bold text-gold" style={{ fontFamily: "var(--font-display)" }}>
            {club.goals}
          </p>
          <p className="text-[10px] sm:text-xs text-white/30 uppercase tracking-wide">Buts</p>
        </div>
        <div>
          <p className="text-xl sm:text-2xl font-bold text-white/70" style={{ fontFamily: "var(--font-display)" }}>
            {club.appearances}
          </p>
          <p className="text-[10px] sm:text-xs text-white/30 uppercase tracking-wide">Matchs</p>
        </div>
        <div>
          <p className="text-xl sm:text-2xl font-bold text-white/70" style={{ fontFamily: "var(--font-display)" }}>
            {ratio}
          </p>
          <p className="text-[10px] sm:text-xs text-white/30 uppercase tracking-wide">Ratio</p>
        </div>
      </div>

      {/* Mini progress */}
      <div className="mt-4">
        <div className="h-1.5 bg-white/5 rounded-full overflow-hidden">
          <div
            className="h-full rounded-full transition-all duration-1000"
            style={{ width: `${percentage}%`, backgroundColor: club.color }}
          />
        </div>
        <p className="text-[10px] text-white/20 mt-1">{percentage}% du total</p>
      </div>
    </div>
  );
}

export default function StatsPage() {
  const totalAppearances = CLUB_STATS.reduce((acc, c) => acc + c.appearances, 0);
  const { club: clubGoals, international: intlGoals } = getGoalsByType();
  const bestClub = CLUB_STATS.reduce((a, b) => (a.goals > b.goals ? a : b));

  return (
    <div className="px-4 py-12 max-w-6xl mx-auto">
      {/* Header */}
      <div className="text-center mb-12">
        <h1
          className="text-3xl sm:text-4xl md:text-5xl font-bold mb-3"
          style={{ fontFamily: "var(--font-display)" }}
        >
          <span className="text-white/80">Les stats de </span>
          <span className="animate-shimmer">CR7</span>
        </h1>
        <p className="text-white/40 text-sm sm:text-base max-w-xl mx-auto">
          {CURRENT_GOALS} buts en {totalAppearances} matchs. Chaque chiffre raconte une partie de la légende.
        </p>
      </div>

      {/* Overview cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 sm:gap-4 mb-12">
        <StatsCard label="Total buts" value={CURRENT_GOALS} highlight delay={0} />
        <StatsCard label="Buts en club" value={clubGoals} delay={0.1} />
        <StatsCard label="Buts internationaux" value={intlGoals} delay={0.2} />
        <StatsCard label="Matchs joués" value={totalAppearances} delay={0.3} />
      </div>

      {/* By Club */}
      <h2
        className="text-xl sm:text-2xl font-bold mb-6"
        style={{ fontFamily: "var(--font-display)" }}
      >
        <span className="text-gold">Par club</span>
      </h2>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 mb-16">
        {CLUB_STATS.map((club) => (
          <ClubCard key={club.club} club={club} />
        ))}
      </div>

      {/* By Competition */}
      <h2
        className="text-xl sm:text-2xl font-bold mb-6"
        style={{ fontFamily: "var(--font-display)" }}
      >
        <span className="text-gold">Par compétition</span>
      </h2>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-16">
        {COMPETITION_STATS.sort((a, b) => b.goals - a.goals).map((comp, i) => (
          <div
            key={comp.competition}
            className="flex items-center justify-between bg-white/[0.02] border border-white/5 rounded-xl p-4 hover:border-white/10 transition-colors"
          >
            <div className="flex items-center gap-3">
              <span className="text-xs text-white/20 w-6 text-right">#{i + 1}</span>
              <span className="text-sm text-white/70">{comp.competition}</span>
            </div>
            <div className="flex items-center gap-3">
              <span className="text-xs text-white/30">{comp.appearances} matchs</span>
              <span className="text-base font-bold text-gold" style={{ fontFamily: "var(--font-display)" }}>
                {comp.goals}
              </span>
            </div>
          </div>
        ))}
      </div>

      {/* Records */}
      <h2
        className="text-xl sm:text-2xl font-bold mb-6"
        style={{ fontFamily: "var(--font-display)" }}
      >
        <span className="text-gold">Records</span>
      </h2>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <div className="bg-white/[0.02] border border-white/5 rounded-xl p-5">
          <p className="text-xs text-white/30 uppercase tracking-wide mb-1">Meilleur buteur international</p>
          <p className="text-lg font-bold text-white/80">143 buts avec le Portugal</p>
          <p className="text-xs text-white/25 mt-1">Record absolu de l&apos;histoire du football</p>
        </div>
        <div className="bg-white/[0.02] border border-white/5 rounded-xl p-5">
          <p className="text-xs text-white/30 uppercase tracking-wide mb-1">Plus gros total dans un club</p>
          <p className="text-lg font-bold text-white/80">{bestClub.goals} buts au {bestClub.club}</p>
          <p className="text-xs text-white/25 mt-1">En {bestClub.appearances} apparitions ({bestClub.years})</p>
        </div>
        <div className="bg-white/[0.02] border border-white/5 rounded-xl p-5">
          <p className="text-xs text-white/30 uppercase tracking-wide mb-1">Ligue des Champions</p>
          <p className="text-lg font-bold text-white/80">141 buts — Meilleur buteur all-time</p>
          <p className="text-xs text-white/25 mt-1">5 titres de Champions League</p>
        </div>
        <div className="bg-white/[0.02] border border-white/5 rounded-xl p-5">
          <p className="text-xs text-white/30 uppercase tracking-wide mb-1">100+ buts dans 4 clubs</p>
          <p className="text-lg font-bold text-white/80">Seul joueur de l&apos;histoire</p>
          <p className="text-xs text-white/25 mt-1">Man Utd, Real Madrid, Juventus, Al Nassr</p>
        </div>
      </div>
    </div>
  );
}
