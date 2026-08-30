const ROUTES_AUTORISEES = new Set([
  "health",
  "v1/catalogue",
  "v1/prevision",
  "v1/recommandation",
]);

export default defineEventHandler(async (event) => {
  const route = getRouterParam(event, "path") || "";
  if (!ROUTES_AUTORISEES.has(route)) {
    throw createError({ statusCode: 404, message: "Route inconnue" });
  }

  const configuration = useRuntimeConfig(event);
  const methode = getMethod(event);
  const corps = methode === "GET" ? undefined : await readRawBody(event);
  try {
    const reponse = await fetch(`${configuration.woyofalApiUrl}/${route}`, {
      method: methode,
      headers: { "Content-Type": "application/json" },
      body: corps,
      signal: AbortSignal.timeout(180_000),
    });
    const contenu = await reponse.json();
    setResponseStatus(event, reponse.status);
    return contenu;
  } catch {
    throw createError({
      statusCode: 503,
      message: "Le moteur de recommandation ne répond pas. Réessayez dans un instant.",
    });
  }
});
