import { readFileSync, readdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const components = join(root, "components");
const required = [
  ["KanbanBoard.tsx", ["Move to", "onKeyDown", "htmlFor", "ArrowRight"]],
  ["LoginView.tsx", ["htmlFor=\"login-email\"", "htmlFor=\"login-password\"", "role=\"alert\""]],
  ["SentimentCharts.tsx", ["role=\"img\"", "aria-label", "role=\"meter\""]],
  ["TopBar.tsx", ["aria-label=\"Filter tickets", "aria-label=\"Sign out\""]],
  ["SignalsView.tsx", ["htmlFor=\"interest-topic\"", "role=\"tablist\""]],
];

const globals = readFileSync(join(root, "app", "globals.css"), "utf8");
if (!globals.includes("prefers-reduced-motion")) {
  console.error("globals.css missing prefers-reduced-motion rules");
  process.exit(1);
}

let failed = false;
for (const [file, needles] of required) {
  const source = readFileSync(join(components, file), "utf8");
  for (const needle of needles) {
    if (!source.includes(needle)) {
      console.error(`${file} missing ${needle}`);
      failed = true;
    }
  }
}

const files = readdirSync(components).filter((name) => name.endsWith(".tsx"));
if (files.length < 10) {
  console.error("expected component tree for a11y contracts");
  failed = true;
}

if (failed) process.exit(1);
console.log(`a11y contracts ok (${required.length} files, reduced-motion present)`);
