<script setup lang="ts">
import {
  AlertTriangle, ArrowLeft, ArrowRight, BatteryCharging, CalendarDays, Check,
  ChevronDown, CirclePower, Clock3, Droplets, Flame, Gauge, House, Info, Leaf,
  Lightbulb, LoaderCircle, Minus, Plus, Plug, Refrigerator, Snowflake, Sparkles,
  Trash2, Tv, Users, WashingMachine, Wind, Zap, type LucideIcon,
} from "@lucide/vue";

type Occupation = "auto" | "oui" | "non";
type TypePiece = "chambre" | "salon" | "autre";
type TaillePiece = "petite" | "moyenne" | "grande";
type ProfilOccupation = "nuit" | "soiree" | "journee" | "variable" | "toujours";

type PieceFormulaire = {
  id: number; nom: string; type_piece: TypePiece; taille: TaillePiece;
  nombre_climatiseurs: number; nombre_ventilateurs: number;
  puissance_climatisation_w: string; puissance_ventilateur_w: string;
  profil_occupation: ProfilOccupation; occupation_actuelle: Occupation;
};

type AppareilFormulaire = {
  type_appareil: string; nom: string; description: string; puissanceDefaut: number;
  quantite: number; puissance_w: string; icone: LucideIcon; decalage: boolean;
};

type RecommandationPiece = {
  piece: string; mode: string; consigne_c: number | null; explication: string;
  occupation_estimee: boolean; temperature_interieure_estimee_c: number;
};

type ReponseRecommandation = {
  source_politique: string; source_meteo: string;
  recommandation_immediate: {
    horodatage: string; temperature_exterieure_c: number;
    credit_restant_apres_pas_kwh: number; consommation_estimee_pas_kwh: number;
    detail_consommation_pas_kwh: Record<string, number>;
    recommandations_pieces: RecommandationPiece[]; recommandation_appareil: string | null;
  };
  credit_estime_fin_horizon_kwh: number;
  planning_par_piece: Record<string, Array<{ debut: string; fin: string; mode: string; consigne_c: number | null }>>;
  inventaire_interprete: {
    pieces: Array<Record<string, string | number | boolean | null>>;
    appareils: Array<{ nom: string; quantite: number; puissance_unitaire_w: number; puissance_installee_w: number }>;
  };
  avertissements: string[];
};

type ReponsePrevision = {
  source_politique: string; simulations: number; duree_mediane_heures: number;
  duree_p10_heures: number; duree_p90_heures: number;
  probabilite_atteindre_date: number | null; credit_final_median_kwh: number;
};

const dateDansSeptJours = () => {
  const date = new Date();
  date.setDate(date.getDate() + 7);
  return date.toISOString().slice(0, 10);
};

const etapes = ["Crédit", "Pièces", "Appareils", "Votre plan"];
const etape = ref(0);
const occupants = ref(5);
const credit = ref("20");
const avecDateCible = ref(true);
const dateCible = ref(dateDansSeptJours());
const moisPrecedent = ref("");
const consommationVeille = ref("");
const afficherPuissances = ref(false);
const chargement = ref(false);
const erreur = ref("");
const recommandation = ref<ReponseRecommandation | null>(null);
const prevision = ref<ReponsePrevision | null>(null);

const pieces = ref<PieceFormulaire[]>([
  { id: 1, nom: "Salon", type_piece: "salon", taille: "grande", nombre_climatiseurs: 0, nombre_ventilateurs: 1, puissance_climatisation_w: "", puissance_ventilateur_w: "", profil_occupation: "soiree", occupation_actuelle: "auto" },
  { id: 2, nom: "Chambre 1", type_piece: "chambre", taille: "moyenne", nombre_climatiseurs: 1, nombre_ventilateurs: 1, puissance_climatisation_w: "", puissance_ventilateur_w: "", profil_occupation: "nuit", occupation_actuelle: "auto" },
]);

const appareils = ref<AppareilFormulaire[]>([
  { type_appareil: "eclairage_led", nom: "Éclairage LED", description: "Ampoules du foyer", puissanceDefaut: 9, quantite: 6, puissance_w: "", icone: Lightbulb, decalage: false },
  { type_appareil: "television", nom: "Télévision", description: "Téléviseurs utilisés", puissanceDefaut: 75, quantite: 1, puissance_w: "", icone: Tv, decalage: false },
  { type_appareil: "refrigerateur", nom: "Réfrigérateur", description: "Fonctionne par cycles", puissanceDefaut: 120, quantite: 1, puissance_w: "", icone: Refrigerator, decalage: false },
  { type_appareil: "congelateur", nom: "Congélateur", description: "Appareil séparé", puissanceDefaut: 160, quantite: 0, puissance_w: "", icone: Snowflake, decalage: false },
  { type_appareil: "petits_appareils", nom: "Box & chargeurs", description: "Routeur, décodeur et veilles", puissanceDefaut: 35, quantite: 1, puissance_w: "", icone: Plug, decalage: false },
  { type_appareil: "fer", nom: "Fer à repasser", description: "Peut être décalé", puissanceDefaut: 1200, quantite: 0, puissance_w: "", icone: Sparkles, decalage: true },
  { type_appareil: "pompe_eau", nom: "Pompe à eau", description: "Peut être décalée", puissanceDefaut: 750, quantite: 0, puissance_w: "", icone: Droplets, decalage: true },
  { type_appareil: "lave_linge", nom: "Lave-linge", description: "Peut être décalé", puissanceDefaut: 500, quantite: 0, puissance_w: "", icone: WashingMachine, decalage: true },
  { type_appareil: "chauffe_eau", nom: "Chauffe-eau", description: "Usage programmable", puissanceDefaut: 1500, quantite: 0, puissance_w: "", icone: Flame, decalage: true },
  { type_appareil: "cuisson_electrique", nom: "Cuisson électrique", description: "Plaque ou cuisinière", puissanceDefaut: 1500, quantite: 0, puissance_w: "", icone: CirclePower, decalage: false },
]);

const compteurs = computed(() => ({
  climatiseurs: pieces.value.reduce((somme, piece) => somme + piece.nombre_climatiseurs, 0),
  ventilateurs: pieces.value.reduce((somme, piece) => somme + piece.nombre_ventilateurs, 0),
  appareils: appareils.value.reduce((somme, appareil) => somme + appareil.quantite, 0),
}));

function changerQuantite(valeur: number, delta: number, maximum: number) {
  return Math.min(maximum, Math.max(0, valeur + delta));
}

function ajouterPiece() {
  const id = Math.max(0, ...pieces.value.map((piece) => piece.id)) + 1;
  const numeroChambre = pieces.value.filter((piece) => piece.type_piece === "chambre").length + 1;
  pieces.value.push({ id, nom: `Chambre ${numeroChambre}`, type_piece: "chambre", taille: "moyenne", nombre_climatiseurs: 0, nombre_ventilateurs: 1, puissance_climatisation_w: "", puissance_ventilateur_w: "", profil_occupation: "nuit", occupation_actuelle: "auto" });
}

function supprimerPiece(id: number) {
  pieces.value = pieces.value.filter((piece) => piece.id !== id);
}

function validerEtape() {
  erreur.value = "";
  if (etape.value === 0 && (!Number(credit.value) || Number(credit.value) < 0)) {
    erreur.value = "Indiquez le crédit en kWh affiché avec le code 801."; return;
  }
  if (etape.value === 1 && pieces.value.some((piece) => !piece.nom.trim())) {
    erreur.value = "Chaque pièce doit avoir un nom."; return;
  }
  if (etape.value === 2 && !appareils.value.some((appareil) => appareil.quantite > 0)) {
    erreur.value = "Sélectionnez au moins un appareil domestique."; return;
  }
  etape.value = Math.min(3, etape.value + 1);
}

function foyerPourApi() {
  const cible = avecDateCible.value && dateCible.value
    ? new Date(`${dateCible.value}T23:59:00`).toISOString() : null;
  return {
    identifiant_foyer: "foyer-interface",
    nombre_occupants: occupants.value,
    credit_initial_kwh: Number(credit.value),
    date_debut: new Date().toISOString(),
    date_cible: cible,
    source_meteo: "auto_dakar",
    taux_adoption: 1,
    seed: 731,
    pieces: pieces.value.map((piece) => ({
      nom: piece.nom, type_piece: piece.type_piece, taille: piece.taille,
      nombre_climatiseurs: piece.nombre_climatiseurs,
      nombre_ventilateurs: piece.nombre_ventilateurs,
      climatisation: piece.nombre_climatiseurs > 0,
      ventilateur: piece.nombre_ventilateurs > 0,
      puissance_climatisation_w: piece.puissance_climatisation_w ? Number(piece.puissance_climatisation_w) : null,
      puissance_ventilateur_w: piece.puissance_ventilateur_w ? Number(piece.puissance_ventilateur_w) : null,
      profil_occupation: piece.profil_occupation,
      occupation_actuelle: piece.occupation_actuelle === "auto" ? null : piece.occupation_actuelle === "oui",
    })),
    appareils: appareils.value.filter((appareil) => appareil.quantite > 0).map((appareil) => ({
      type_appareil: appareil.type_appareil,
      quantite: appareil.quantite,
      puissance_w: appareil.puissance_w ? Number(appareil.puissance_w) : null,
    })),
    historique_compteur: {
      consommation_mois_precedent_kwh: moisPrecedent.value ? Number(moisPrecedent.value) : null,
      consommation_veille_kwh: consommationVeille.value ? Number(consommationVeille.value) : null,
    },
  };
}

async function analyser() {
  erreur.value = "";
  chargement.value = true;
  etape.value = 3;
  const foyer = foyerPourApi();
  try {
    const [reco, prev] = await Promise.all([
      $fetch<ReponseRecommandation>("/api/woyofal/v1/recommandation", {
        method: "POST", body: { scenario: null, foyer, horizon_heures: 4 },
      }),
      $fetch<ReponsePrevision>("/api/woyofal/v1/prevision", {
        method: "POST", body: { scenario: null, foyer, simulations: 5 },
      }),
    ]);
    recommandation.value = reco;
    prevision.value = prev;
  } catch (cause: any) {
    erreur.value = cause?.data?.statusMessage || cause?.data?.detail || cause?.message || "Une erreur inattendue est survenue.";
  } finally {
    chargement.value = false;
  }
}

function formatDuree(heures: number) {
  if (heures < 24) return `${Math.round(heures)} h`;
  const jours = Math.floor(heures / 24);
  const reste = Math.round(heures % 24);
  return reste ? `${jours} j ${reste} h` : `${jours} jours`;
}

function libelleMode(mode: string) {
  return ({ arret: "Tout arrêter", ventilateur: "Ventilateur", clim_eco_27: "Clim éco · 27 °C", clim_confort_25: "Clim confort · 25 °C", clim_boost_23: "Clim boost · 23 °C" } as Record<string, string>)[mode] || mode;
}

function libelleConsommation(cle: string) {
  return ({ non_pilotable: "Appareils courants", charges_flexibles: "Charges flexibles", climatisation: "Climatisation", ventilateurs: "Ventilateurs" } as Record<string, string>)[cle] || cle;
}
</script>

<template>
  <main class="coquille">
    <header class="entete">
      <a class="marque" href="#haut" aria-label="Accueil Woyofal"><span class="logo"><Zap :size="18" :stroke-width="3" /></span>WOYOFAL</a>
      <div class="etat-api"><span /> Modèle RL actif</div>
    </header>

    <section id="haut" class="intro-produit">
      <div><p class="surtitre">ASSISTANT ÉNERGIE WOYOFAL</p><h1>Votre crédit.<br><em>Plus longtemps.</em></h1></div>
      <p>Une recommandation concrète pour chaque pièce, selon votre crédit, vos appareils, la météo de Dakar et vos habitudes — sans thermomètre ni objet connecté.</p>
    </section>

    <section class="application">
      <nav class="progression" aria-label="Progression du formulaire">
        <button v-for="(libelle, index) in etapes" :key="libelle" type="button" :class="{ active: index === etape, terminee: index < etape }" :disabled="index > etape" @click="index < etape && (etape = index)">
          <span><Check v-if="index < etape" :size="15" /><template v-else>{{ index + 1 }}</template></span>{{ libelle }}
        </button>
      </nav>

      <div class="surface">
        <section v-if="etape === 0" class="etape">
          <div class="titre-etape"><span class="icone-titre"><BatteryCharging /></span><div><p>ÉTAPE 1 SUR 3</p><h2>Votre situation Woyofal</h2><span>Deux informations suffisent pour commencer.</span></div></div>
          <div class="grille-formulaire deux-colonnes">
            <label class="champ important"><span>Crédit disponible <small>Code compteur 801</small></span><div class="saisie-unite"><input v-model="credit" inputmode="decimal" type="number" min="0" step="0.1"><b>kWh</b></div></label>
            <label class="champ"><span>Personnes dans le foyer</span><div class="compteur large"><button type="button" aria-label="Retirer une personne" @click="occupants = Math.max(1, occupants - 1)"><Minus /></button><strong><Users :size="19" /> {{ occupants }}</strong><button type="button" aria-label="Ajouter une personne" @click="occupants = Math.min(20, occupants + 1)"><Plus /></button></div></label>
            <div class="champ pleine-largeur bloc-date">
              <div class="ligne-entete-champ"><span><CalendarDays :size="18" /> Voulez-vous tenir jusqu’à une date précise ?</span><button class="interrupteur" :class="{ actif: avecDateCible }" type="button" role="switch" :aria-checked="avecDateCible" @click="avecDateCible = !avecDateCible"><i /></button></div>
              <label v-if="avecDateCible" class="date-cible"><span>Prochaine recharge prévue</span><input v-model="dateCible" type="date" :min="new Date().toISOString().slice(0, 10)"></label>
              <p v-else class="aide">Le modèle cherchera à faire durer le crédit le plus longtemps possible, jusqu’à 30 jours.</p>
            </div>
          </div>
          <details class="details-optionnels"><summary><Gauge :size="18" /> Ajouter mes anciennes consommations <small>optionnel, mais plus précis</small><ChevronDown /></summary><div class="grille-formulaire deux-colonnes"><label class="champ"><span>Mois précédent <small>Code 820</small></span><div class="saisie-unite"><input v-model="moisPrecedent" type="number" min="0" step="0.1" placeholder="Ex. 92"><b>kWh</b></div></label><label class="champ"><span>Consommation d’hier</span><div class="saisie-unite"><input v-model="consommationVeille" type="number" min="0" step="0.1" placeholder="Ex. 3,1"><b>kWh</b></div></label></div></details>
        </section>

        <section v-else-if="etape === 1" class="etape">
          <div class="titre-etape avec-action"><span class="icone-titre"><House /></span><div><p>ÉTAPE 2 SUR 3</p><h2>Les pièces à piloter</h2><span>Ajoutez les espaces avec climatisation ou ventilateur.</span></div><button class="bouton-secondaire" type="button" @click="ajouterPiece"><Plus /> Ajouter une pièce</button></div>
          <div class="resume-inventaire"><span><Snowflake /> {{ compteurs.climatiseurs }} clim{{ compteurs.climatiseurs > 1 ? "s" : "" }}</span><span><Wind /> {{ compteurs.ventilateurs }} ventilateur{{ compteurs.ventilateurs > 1 ? "s" : "" }}</span><span>Aucune pièce n’est prioritaire</span></div>
          <div class="liste-pieces">
            <article v-for="(piece, index) in pieces" :key="piece.id" class="carte-piece">
              <div class="numero-piece">{{ String(index + 1).padStart(2, "0") }}</div>
              <div class="corps-piece">
                <div class="ligne-piece"><label class="champ nom-piece"><span>Nom de la pièce</span><input v-model="piece.nom"></label><button v-if="pieces.length > 1" class="supprimer" type="button" :aria-label="`Supprimer ${piece.nom}`" @click="supprimerPiece(piece.id)"><Trash2 /></button></div>
                <div class="grille-piece">
                  <label class="champ"><span>Type</span><select v-model="piece.type_piece"><option value="chambre">Chambre</option><option value="salon">Salon</option><option value="autre">Autre espace</option></select></label>
                  <label class="champ"><span>Taille approximative</span><select v-model="piece.taille"><option value="petite">Petite</option><option value="moyenne">Moyenne</option><option value="grande">Grande</option></select></label>
                  <label class="champ"><span>Occupation habituelle</span><select v-model="piece.profil_occupation"><option value="nuit">Surtout la nuit</option><option value="soiree">Surtout le soir</option><option value="journee">Surtout la journée</option><option value="variable">Variable</option><option value="toujours">Presque toujours</option></select></label>
                </div>
                <div class="equipements-piece">
                  <div class="equipement-confort" :class="{ selectionne: piece.nombre_climatiseurs }"><span class="visuel-appareil froid"><Snowflake /></span><div><strong>Climatiseur</strong><small>{{ piece.puissance_climatisation_w ? `${piece.puissance_climatisation_w} W chacun` : "Puissance estimée par la taille" }}</small></div><div class="compteur"><button type="button" @click="piece.nombre_climatiseurs = changerQuantite(piece.nombre_climatiseurs, -1, 4)"><Minus /></button><strong>{{ piece.nombre_climatiseurs }}</strong><button type="button" @click="piece.nombre_climatiseurs = changerQuantite(piece.nombre_climatiseurs, 1, 4)"><Plus /></button></div></div>
                  <div class="equipement-confort" :class="{ selectionne: piece.nombre_ventilateurs }"><span class="visuel-appareil air"><Wind /></span><div><strong>Ventilateur</strong><small>{{ piece.puissance_ventilateur_w ? `${piece.puissance_ventilateur_w} W chacun` : "55 W estimés par appareil" }}</small></div><div class="compteur"><button type="button" @click="piece.nombre_ventilateurs = changerQuantite(piece.nombre_ventilateurs, -1, 8)"><Minus /></button><strong>{{ piece.nombre_ventilateurs }}</strong><button type="button" @click="piece.nombre_ventilateurs = changerQuantite(piece.nombre_ventilateurs, 1, 8)"><Plus /></button></div></div>
                </div>
                <details v-if="piece.nombre_climatiseurs || piece.nombre_ventilateurs" class="puissances-piece"><summary>Je connais la puissance des appareils <ChevronDown /></summary><div><label v-if="piece.nombre_climatiseurs" class="champ"><span>Puissance d’une clim</span><div class="saisie-unite"><input v-model="piece.puissance_climatisation_w" type="number" min="1" placeholder="Auto"><b>W</b></div></label><label v-if="piece.nombre_ventilateurs" class="champ"><span>Puissance d’un ventilateur</span><div class="saisie-unite"><input v-model="piece.puissance_ventilateur_w" type="number" min="1" placeholder="Auto"><b>W</b></div></label></div></details>
                <div class="occupation-actuelle"><span><Clock3 /> La pièce est-elle occupée maintenant ?</span><div><button v-for="choix in (['auto', 'oui', 'non'] as Occupation[])" :key="choix" type="button" :class="{ actif: piece.occupation_actuelle === choix }" @click="piece.occupation_actuelle = choix">{{ choix === "auto" ? "Selon le profil" : choix === "oui" ? "Oui" : "Non" }}</button></div></div>
              </div>
            </article>
          </div>
        </section>

        <section v-else-if="etape === 2" class="etape">
          <div class="titre-etape avec-action"><span class="icone-titre"><Plug /></span><div><p>ÉTAPE 3 SUR 3</p><h2>Vos appareils électriques</h2><span>Mettez la quantité à zéro si vous n’avez pas l’appareil.</span></div><button class="bouton-secondaire" :class="{ actif: afficherPuissances }" type="button" @click="afficherPuissances = !afficherPuissances"><Gauge /> Puissances {{ afficherPuissances ? "visibles" : "optionnelles" }}</button></div>
          <div class="grille-appareils">
            <article v-for="appareil in appareils" :key="appareil.type_appareil" class="carte-appareil" :class="{ selectionnee: appareil.quantite }">
              <div class="haut-appareil"><span class="visuel-appareil"><component :is="appareil.icone" /></span><span v-if="appareil.decalage" class="etiquette-decalable">Décalable</span></div><h3>{{ appareil.nom }}</h3><p>{{ appareil.description }}</p>
              <div class="bas-appareil"><div class="compteur"><button type="button" @click="appareil.quantite = changerQuantite(appareil.quantite, -1, 30)"><Minus /></button><strong>{{ appareil.quantite }}</strong><button type="button" @click="appareil.quantite = changerQuantite(appareil.quantite, 1, 30)"><Plus /></button></div><small>{{ appareil.puissance_w || appareil.puissanceDefaut }} W / unité</small></div>
              <label v-if="afficherPuissances && appareil.quantite" class="puissance-appareil"><span>Puissance réelle par unité</span><div class="saisie-unite"><input v-model="appareil.puissance_w" type="number" min="1" :placeholder="String(appareil.puissanceDefaut)"><b>W</b></div></label>
            </article>
          </div>
          <div class="note-realisme"><Info /><p><strong>Pourquoi demander les quantités ?</strong> Deux télévisions ou dix ampoules ne produisent pas le même profil. Si vous ne connaissez pas les watts, Woyofal utilise une estimation documentée.</p></div>
        </section>

        <section v-else class="etape resultat">
          <div v-if="chargement" class="chargement"><span class="orbite"><LoaderCircle /><i /></span><p>LE DQN ANALYSE VOTRE FOYER</p><h2>Construction du meilleur plan…</h2><div class="points-chargement"><span>Simulation des usages</span><span>Estimation thermique</span><span>Comparaison des décisions</span></div><small>Les consommations restent des estimations recalibrables avec vos lectures Woyofal.</small></div>
          <div v-else-if="erreur" class="erreur-resultat"><AlertTriangle /><h2>Impossible de terminer l’analyse</h2><p>{{ erreur }}</p><button class="bouton-principal" type="button" @click="etape = 2"><ArrowLeft /> Vérifier mes informations</button></div>
          <template v-else-if="recommandation && prevision">
            <div class="entete-resultat"><div><p class="surtitre">VOTRE PLAN ÉNERGIE</p><h2>{{ prevision.probabilite_atteindre_date !== null && prevision.probabilite_atteindre_date >= .7 ? "Votre objectif est à portée." : "Votre crédit demande de vrais arbitrages." }}</h2><span>Calculé par {{ recommandation.source_politique.toUpperCase() }} · à recalculer toutes les 30 minutes</span></div><button class="bouton-secondaire" type="button" @click="etape = 0"><ArrowLeft /> Modifier le foyer</button></div>
            <div class="indicateurs"><article class="indicateur principal"><span><Leaf /></span><small>{{ avecDateCible ? "Chance d’atteindre la date" : "Durée médiane estimée" }}</small><strong>{{ avecDateCible && prevision.probabilite_atteindre_date !== null ? `${Math.round(prevision.probabilite_atteindre_date * 100)} %` : formatDuree(prevision.duree_mediane_heures) }}</strong><p>{{ avecDateCible ? `${prevision.simulations} simulations stochastiques` : `entre ${formatDuree(prevision.duree_p10_heures)} et ${formatDuree(prevision.duree_p90_heures)}` }}</p></article><article class="indicateur"><span><BatteryCharging /></span><small>Crédit après 30 min</small><strong>{{ recommandation.recommandation_immediate.credit_restant_apres_pas_kwh.toFixed(2) }} kWh</strong><p>{{ recommandation.recommandation_immediate.consommation_estimee_pas_kwh.toFixed(3) }} kWh demandés</p></article><article class="indicateur"><span><Clock3 /></span><small>Autonomie médiane</small><strong>{{ formatDuree(prevision.duree_mediane_heures) }}</strong><p>P10 {{ formatDuree(prevision.duree_p10_heures) }} · P90 {{ formatDuree(prevision.duree_p90_heures) }}</p></article></div>
            <div class="grille-resultats">
              <section class="bloc-resultat recommandations"><div class="titre-bloc"><div><p>À FAIRE MAINTENANT</p><h3>Confort pièce par pièce</h3></div><span>{{ new Date(recommandation.recommandation_immediate.horodatage).toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' }) }}</span></div><div class="liste-recommandations"><article v-for="item in recommandation.recommandation_immediate.recommandations_pieces" :key="item.piece"><span class="mode-icone" :class="item.mode"><Wind v-if="item.mode === 'ventilateur'" /><CirclePower v-else-if="item.mode === 'arret'" /><Snowflake v-else /></span><div><strong>{{ item.piece }}</strong><p>{{ item.occupation_estimee ? "Occupée" : "Estimée vide" }} · {{ item.temperature_interieure_estimee_c.toFixed(1) }} °C estimés</p></div><b>{{ libelleMode(item.mode) }}</b></article></div><div v-if="recommandation.recommandation_immediate.recommandation_appareil" class="alerte-appareil"><Clock3 /><span><strong>Appareil énergivore</strong>{{ recommandation.recommandation_immediate.recommandation_appareil }}</span></div></section>
              <aside class="bloc-resultat consommation"><div class="titre-bloc"><div><p>PROCHAINES 30 MINUTES</p><h3>Consommation estimée</h3></div><Gauge /></div><div class="barres-energie"><div v-for="(valeur, cle) in recommandation.recommandation_immediate.detail_consommation_pas_kwh" :key="cle"><span><b>{{ libelleConsommation(cle) }}</b><small>{{ valeur.toFixed(3) }} kWh</small></span><i><em :style="{ width: `${Math.max(2, valeur / Math.max(recommandation.recommandation_immediate.consommation_estimee_pas_kwh, .001) * 100)}%` }" /></i></div></div><div class="meteo"><span><Wind /></span><p><small>Météo extérieure</small><strong>{{ recommandation.recommandation_immediate.temperature_exterieure_c.toFixed(1) }} °C</strong></p></div></aside>
            </div>
            <details class="inventaire-compris"><summary><Check /> Vérifier ce que le modèle a compris de mon foyer <ChevronDown /></summary><div><section><h4>Pièces</h4><p v-for="piece in recommandation.inventaire_interprete.pieces" :key="String(piece.nom)"><strong>{{ piece.nom }}</strong><span>{{ piece.nombre_climatiseurs }} clim · {{ piece.nombre_ventilateurs }} ventilo · {{ piece.puissance_climatisation_totale_w }} W clim installés</span></p></section><section><h4>Appareils</h4><p v-for="appareil in recommandation.inventaire_interprete.appareils" :key="appareil.nom"><strong>{{ appareil.nom }}</strong><span>{{ appareil.quantite }} × {{ appareil.puissance_unitaire_w }} W</span></p></section></div></details>
            <div class="avertissement"><AlertTriangle /><p><strong>Une aide à la décision, pas une mesure du compteur.</strong> {{ recommandation.avertissements.join(" ") }} Source météo : {{ recommandation.source_meteo.replaceAll("_", " ") }}.</p></div>
          </template>
          <div v-else class="pret-analyse"><span><Sparkles /></span><h2>Votre foyer est prêt</h2><p>{{ pieces.length }} pièces, {{ compteurs.climatiseurs }} climatisation{{ compteurs.climatiseurs > 1 ? "s" : "" }}, {{ compteurs.ventilateurs }} ventilateur{{ compteurs.ventilateurs > 1 ? "s" : "" }} et {{ compteurs.appareils }} appareils déclarés.</p><button class="bouton-principal grand" type="button" @click="analyser"><Zap /> Lancer l’analyse RL</button><small>Calcul local · environ 10 à 30 secondes</small></div>
        </section>

        <p v-if="erreur && etape < 3" class="message-erreur"><AlertTriangle /> {{ erreur }}</p>
        <footer v-if="etape < 3" class="actions-formulaire"><button class="bouton-retour" type="button" :disabled="etape === 0" @click="erreur = ''; etape = Math.max(0, etape - 1)"><ArrowLeft /> Retour</button><button class="bouton-principal" type="button" @click="validerEtape">{{ etape < 2 ? "Continuer" : "Voir le récapitulatif" }} <ArrowRight /></button></footer>
      </div>
    </section>
    <footer class="pied-page"><span>Woyofal n’accède pas automatiquement à votre compteur.</span><span>Vos informations restent dans votre déploiement.</span></footer>
  </main>
</template>
