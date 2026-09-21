import { readFileSync, writeFileSync, renameSync } from "node:fs";
import { createHash } from "node:crypto";

const canonical = (value) => {
  if (Array.isArray(value)) return `[${value.map(canonical).join(",")}]`;
  if (value !== null && typeof value === "object") {
    return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${canonical(value[key])}`).join(",")}}`;
  }
  return JSON.stringify(value);
};
const digest = (value) => createHash("sha256").update(canonical(value)).digest("hex");

export default function (pi) {
  const configPath = process.env.RAR_PI_RUN_CONFIG;
  const receiptPath = process.env.RAR_PI_RUN_RECEIPT;
  let config;
  let initialDigest;
  let requests = 0;
  const stop = () => {
    // Pi catches handler exceptions and may send the unchanged payload.
    // Termination must happen synchronously before returning to the adapter.
    process.stderr.write("Request policy enforcement failed.\n");
    process.exit(78);
  };
  const record = (state) => {
    writeFileSync(`${receiptPath}.tmp`, JSON.stringify({
      state, model: config.model, gateway: config.gateway,
      config_sha256: initialDigest, request_count: requests,
      policy_sha256: config.policy ? digest(config.policy) : null,
    }), { mode: 0o600 });
    renameSync(`${receiptPath}.tmp`, receiptPath);
  };
  const check = async (ctx) => {
    if (digest(JSON.parse(readFileSync(configPath, "utf8"))) !== initialDigest) stop();
    if (ctx.model?.id !== config.model || ctx.model?.provider !== config.gateway) stop();
    if (ctx.model?.api !== "openai-completions") stop();
    if (ctx.model?.baseUrl?.replace(/\/$/, "") !== config.base_url) stop();
    const auth = await ctx.modelRegistry.getApiKeyAndHeaders(ctx.model);
    if (!auth.ok || (auth.baseUrl && auth.baseUrl.replace(/\/$/, "") !== config.base_url)) stop();
    if (config.image_input && !ctx.model?.input?.includes("image")) stop();
  };
  try {
    config = JSON.parse(readFileSync(configPath, "utf8"));
    initialDigest = digest(config);
    if (config.gateway !== "openrouter" || !config.model) stop();
    if (config.policy && (config.policy.gateway !== config.gateway || config.policy.zdr !== true
      || config.policy.data_collection !== "deny" || config.policy.require_parameters !== true)) stop();
  } catch { stop(); }
  pi.on("session_start", async (_event, ctx) => {
    try { await check(ctx); record("ready"); } catch { stop(); }
  });
  pi.on("before_provider_request", async (event, ctx) => {
    try {
      await check(ctx);
      if (!event.payload || event.payload.model !== config.model) stop();
      const payload = { ...event.payload };
      if (config.policy) {
        const { gateway, ...provider } = config.policy;
        payload.provider = provider;
      }
      if (config.effort_control === "runtime") {
        delete payload.reasoning;
        delete payload.reasoning_effort;
      } else if (config.effort !== null) {
        delete payload.reasoning_effort;
        payload.reasoning = config.effort === "off"
          ? { enabled: false } : { effort: config.effort };
      }
      if (config.tools !== null) {
        const names = (payload.tools || []).map((tool) => tool.function?.name).sort();
        if (canonical(names) !== canonical([...config.tools].sort())) stop();
      }
      if (requests === 0 && config.initial_image_count) {
        const images = (payload.messages || []).flatMap((message) => Array.isArray(message.content) ? message.content : [])
          .filter((part) => part.type === "image_url" && part.image_url?.url?.startsWith("data:image/"));
        if (images.length < config.initial_image_count) stop();
      }
      requests += 1;
      record("enforced");
      return payload;
    } catch { stop(); }
  });
  // This runtime summarizes outside the request hook. Stop before source leaves it.
  pi.on("session_before_compact", () => stop());
  pi.on("session_before_tree", () => stop());
  pi.on("agent_settled", () => {
    try { record("complete"); } catch { stop(); }
  });
}
