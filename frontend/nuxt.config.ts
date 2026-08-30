export default defineNuxtConfig({
  compatibilityDate: "2026-08-27",
  devtools: { enabled: false },
  css: ["~/globals.css"],
  runtimeConfig: {
    woyofalApiUrl: process.env.WOYOFAL_API_URL || "http://127.0.0.1:8000",
  },
  app: {
    head: {
      htmlAttrs: { lang: "fr" },
      title: "Woyofal — Votre crédit Woyofal, mieux piloté",
      meta: [
        {
          name: "description",
          content: "Prévisions et recommandations énergétiques pièce par pièce, propulsées par apprentissage par renforcement.",
        },
      ],
    },
  },
  nitro: { preset: "node-server" },
  // Le contrôle complet est exécuté séparément par `pnpm typecheck`.
  typescript: { typeCheck: false },
});
