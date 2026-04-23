import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "À propos",
  description: "À propos de To1000.com — le compte à rebours vers le 1000e but de Cristiano Ronaldo.",
};

export default function AboutPage() {
  return (
    <div className="px-4 py-12 max-w-3xl mx-auto">
      <h1
        className="text-3xl sm:text-4xl font-bold mb-8 text-center"
        style={{ fontFamily: "var(--font-display)" }}
      >
        <span className="text-white/80">À propos de </span>
        <span className="animate-shimmer">To1000.com</span>
      </h1>

      <div className="space-y-6 text-white/60 text-sm sm:text-base leading-relaxed">
        <p>
          To1000.com est un projet créé par des fans de football pour suivre en temps réel le chemin de
          Cristiano Ronaldo vers son 1000e but en carrière professionnelle. Un exploit qu&apos;aucun joueur
          n&apos;a jamais accompli dans l&apos;ère moderne du football.
        </p>

        <p>
          Le compteur est basé sur une estimation mathématique utilisant le rythme de buts récent de CR7
          (buts par match × fréquence des matchs). Les données sont mises à jour après chaque match.
        </p>

        <div className="bg-white/[0.02] border border-white/5 rounded-xl p-6">
          <h2 className="text-lg font-bold text-white/80 mb-3">Sources des données</h2>
          <div className="space-y-2">
            <p>
              <a href="https://www.espn.com/soccer/story/_/id/46751020/cristiano-ronaldo-goal-tracker-road-1000-career-goals" target="_blank" rel="noopener noreferrer" className="text-gold hover:underline">ESPN Goal Tracker</a>
              {" "}— Suivi officiel des buts de CR7
            </p>
            <p>
              <a href="https://www.transfermarkt.fr/cristiano-ronaldo/alletore/spieler/8198" target="_blank" rel="noopener noreferrer" className="text-gold hover:underline">Transfermarkt</a>
              {" "}— Statistiques détaillées par match
            </p>
            <p>
              <a href="https://en.wikipedia.org/wiki/List_of_career_achievements_by_Cristiano_Ronaldo" target="_blank" rel="noopener noreferrer" className="text-gold hover:underline">Wikipedia</a>
              {" "}— Records et achievements
            </p>
          </div>
        </div>

        <div className="bg-white/[0.02] border border-white/5 rounded-xl p-6">
          <h2 className="text-lg font-bold text-white/80 mb-3">Méthodologie du compteur</h2>
          <p className="mb-2">
            Le compte à rebours est calculé avec la formule suivante :
          </p>
          <div className="bg-black/30 rounded-lg p-4 font-mono text-xs text-gold/70">
            <p>jours_estimés = buts_restants / (buts_par_match × matchs_par_jour)</p>
            <p className="text-white/30 mt-2">
              Avec un rythme actuel de ~0.85 but/match et ~2 matchs/semaine
            </p>
          </div>
        </div>

        <div className="bg-white/[0.02] border border-white/5 rounded-xl p-6">
          <h2 className="text-lg font-bold text-white/80 mb-3">Mentions légales</h2>
          <p className="text-xs text-white/30">
            Ce site est un projet non officiel créé par des fans. Il n&apos;est en aucun cas affilié à,
            approuvé par, ou associé à Cristiano Ronaldo, ses agents, ses clubs actuels ou passés,
            ou toute autre entité liée. Tous les noms, logos et images sont la propriété de leurs
            détenteurs respectifs. Les statistiques sont compilées à partir de sources publiques.
          </p>
        </div>

        <p className="text-center text-white/20 text-xs pt-6">
          Fait avec passion — To1000.com © 2026
        </p>
      </div>
    </div>
  );
}
