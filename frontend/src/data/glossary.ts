// Glossaire débutant — définitions vulgarisées des termes financiers affichés dans l'UI.
// `learnQuery` alimente le lien « En savoir plus » vers la recherche sémantique (corpus RAG).
// Source de vérité unique : tout terme rendu via <GlossaryTerm term="..."> doit exister ici.

export interface GlossaryEntry {
  /** Libellé court affiché à l'utilisateur (ex. « P/E »). */
  label: string
  /** Définition en une à trois phrases, sans jargon. */
  definition: string
  /** Requête envoyée à la recherche sémantique pour approfondir. Optionnelle. */
  learnQuery?: string
}

export const GLOSSARY: Record<string, GlossaryEntry> = {
  pe: {
    label: 'P/E',
    definition:
      "Ratio cours/bénéfice. Combien tu paies pour 1 $ de profit annuel de l'entreprise. " +
      'Un P/E de 11 = tu paies 11 $ pour 1 $ de bénéfice. Plus bas = moins cher, à qualité égale.',
    learnQuery: 'ratio cours bénéfice P/E interprétation Graham',
  },
  dividende: {
    label: 'Dividende',
    definition:
      "Part du profit qu'une entreprise verse à ses actionnaires, souvent chaque trimestre. " +
      "C'est un revenu régulier que tu touches simplement en détenant l'action.",
    learnQuery: 'dividende rendement versement actionnaires',
  },
  rendement_dividende: {
    label: 'Rendement du dividende',
    definition:
      'Le dividende annuel exprimé en pourcentage du cours. Un rendement de 4 % = tu reçois ' +
      "4 $ par an pour chaque 100 $ investis, en plus de l'évolution du cours.",
    learnQuery: 'rendement du dividende calcul pourcentage',
  },
  qualite: {
    label: 'Score de qualité',
    definition:
      "Note sur 100 calculée par nos filtres (Graham, Buffett, valorisation, solidité, etc.). " +
      'FORT (≥ 70) = passe la majorité des filtres ; MODÉRÉ (45-69) = correct ; FAIBLE = à éviter.',
    learnQuery: 'score composite qualité entreprise analyse fondamentale',
  },
  volatilite: {
    label: 'Volatilité',
    definition:
      "L'ampleur des variations du cours dans le temps. Forte volatilité = le prix monte et " +
      'descend beaucoup (plus de stress, plus de risque) ; faible = plus stable.',
    learnQuery: 'volatilité risque variation cours action',
  },
  marge_securite: {
    label: 'Marge de sécurité',
    definition:
      "L'écart entre la vraie valeur estimée d'une action et son prix. Acheter sous sa valeur " +
      'te protège si ton estimation était trop optimiste — un principe central de Graham et Klarman.',
    learnQuery: 'marge de sécurité Graham Klarman valeur intrinsèque',
  },
  celi: {
    label: 'CELI',
    definition:
      "Compte d'épargne libre d'impôt. Tes gains (dividendes, plus-values) n'y sont jamais " +
      'imposés. Idéal pour faire croître des placements à long terme à l\'abri de l\'impôt.',
    learnQuery: 'CELI compte épargne libre impôt placements',
  },
  reer: {
    label: 'REER',
    definition:
      "Régime enregistré d'épargne-retraite. Tes cotisations réduisent ton revenu imposable " +
      "aujourd'hui ; tu paies l'impôt plus tard, au retrait (souvent à la retraite, à taux plus bas).",
    learnQuery: 'REER cotisation déduction impôt retraite',
  },
  diversification: {
    label: 'Diversification',
    definition:
      'Répartir ton argent sur plusieurs titres et secteurs plutôt qu\'un seul. Si un placement ' +
      'chute, les autres amortissent — c\'est la règle de base pour réduire le risque.',
    learnQuery: 'diversification portefeuille réduction risque',
  },
  etf: {
    label: 'ETF',
    definition:
      "Fonds négocié en bourse : un panier d'actions acheté en une seule transaction. Un seul " +
      'ETF peut contenir des centaines d\'entreprises — la diversification la plus simple pour débuter.',
    learnQuery: 'ETF fonds indiciel diversification passif',
  },
}

export type GlossaryKey = keyof typeof GLOSSARY
