// Kukicha idiom gate for opencode.
//
// Fires after the agent writes or edits a *.kuki file and enforces the
// idiom rules that AGENTS.md / .agents/skills/kukicha/SKILL.md document but
// that `kukicha check`, `kukicha fmt`, and the LSP do NOT catch (Go-compat
// forms like `==` are valid Go and pass every existing tool silently).
//
// ERRORS  -> throw, which surfaces the failure to the model so it fixes the
//            file before moving on (the write already landed on disk).
// WARNINGS -> appended to the tool output; visible but non-blocking.
//
// Loaded automatically by opencode from .opencode/plugin/. No build step.

import { readFile } from "node:fs/promises"

/** @typedef {import("@opencode-ai/plugin").Plugin} Plugin */

// Tools that land file content on disk.
const WRITE_TOOLS = new Set(["write", "edit", "patch", "multiedit"])

// Strip string literals and trailing # comments from one line so operator
// matching never trips on text inside "...", '...', `...`, or a comment.
// Strings are removed BEFORE comments so a # inside a string is handled.
function stripNonCode(line) {
    let out = ""
    let i = 0
    let quote = null // '"' | "'" | "`" | null
    while (i < line.length) {
        const ch = line[i]
        if (quote) {
            if (ch === "\\" && quote !== "`") {
                i += 2
                continue
            }
            if (ch === quote) quote = null
            i++
            continue
        }
        if (ch === '"' || ch === "'" || ch === "`") {
            quote = ch
            i++
            continue
        }
        if (ch === "#") break // rest of line is a comment
        out += ch
        i++
    }
    return out
}

// Each rule: a regex over a code-only line, a severity, and a hint.
const RULES = [
    {
        id: "go-equals",
        re: /(?<![<>=!:])==(?!=)/,
        severity: "error",
        msg: "`==` is Go syntax — use `equals` (AGENTS.md: \"equals/isnt replace every == and !=\").",
    },
    {
        id: "go-notequals",
        re: /(?<![<>=!])!=(?!=)/,
        severity: "error",
        msg: "`!=` is Go syntax — use `isnt`.",
    },
    {
        id: "go-and",
        re: /&&/,
        severity: "error",
        msg: "`&&` is Go syntax — use `and`.",
    },
    {
        id: "go-or",
        re: /\|\|/,
        severity: "error",
        msg: "`||` is Go syntax — use `or`.",
    },
    {
        id: "go-not",
        // unary ! that isn't part of != ; allow `!=` (already covered) and not inside ident
        re: /(?<![!=])![^=]/,
        severity: "error",
        msg: "`!` is Go syntax — use `not`.",
    },
    {
        id: "go-nil",
        re: /\bnil\b/,
        severity: "error",
        msg: "`nil` is Go — use `empty`.",
    },
    {
        id: "sole-discard",
        // leading `_ =` or `_ :=` — discarding a sole return value
        re: /^\s*_\s*:?=(?!=)/,
        severity: "error",
        msg: "`_ =` / `_ :=` discards a return value (Critical Rule 11). Call it as a bare statement and use `onerr` (or `onerr discard` in test code only).",
    },
    {
        id: "tuple-discard",
        // `x, _ :=` — discarding one slot of a multi-return / comma-ok
        re: /,\s*_\s*:?=(?!=)/,
        severity: "warning",
        msg: "comma-ok discard (`x, _ := ...`): for map reads, a non-comma-ok read yields the zero value (`v := m[k]`); if the `ok` matters, use `maps.GetOr`. If 2+ callers discard the same slot, the signature is wrong (AGENTS.md line ~1048).",
    },
    {
        id: "bare-panic",
        // `panic ...` not reached via `onerr panic`
        re: /(?<!onerr )\bpanic\b/,
        severity: "warning",
        msg: "bare `panic` — prefer returning an error or `onerr panic \"...\"`. Tolerable only in `main`/`init`.",
    },
]

// Detect the `map of string to any` dict-carryover smell: if the multi-token
// type repeats >= 3x in a file with no transparent alias defined, flag it.
function aliasSmell(text) {
    const occurrences = (text.match(/map of string to any/g) || []).length
    const hasAlias = /^\s*type\s+\w+\s*=\s*.*map of string to any/m.test(text)
    if (occurrences >= 3 && !hasAlias) {
        return `\`map of string to any\` appears ${occurrences}x with no transparent alias. AGENTS.md rule of thumb: alias a multi-token type that repeats 3+ times (e.g. \`type Payload = map of string to any\`). If these are structured action/response payloads, prefer the schema structs in game/schemas.kuki over a stringly-typed dict (Python-dict carryover).`
    }
    return null
}

function scan(text) {
    const errors = []
    const warnings = []
    const lines = text.split("\n")
    let inTriple = false
    for (let n = 0; n < lines.length; n++) {
        const raw = lines[n]
        // Track triple-quoted multi-line strings; skip their contents entirely.
        const triples = (raw.match(/"""/g) || []).length
        if (inTriple) {
            if (triples % 2 === 1) inTriple = false
            continue
        }
        if (triples % 2 === 1) {
            inTriple = true
            continue
        }
        const code = stripNonCode(raw)
        if (!code.trim()) continue
        for (const rule of RULES) {
            if (rule.re.test(code)) {
                const entry = { line: n + 1, text: raw.trim(), msg: rule.msg }
                ;(rule.severity === "error" ? errors : warnings).push(entry)
            }
        }
    }
    return { errors, warnings }
}

function fmt(entries) {
    return entries.map((e) => `  L${e.line}: ${e.text}\n        -> ${e.msg}`).join("\n")
}

/** @type {Plugin} */
export const KukichaIdiom = async () => {
    return {
        "tool.execute.after": async (input, output) => {
            if (!WRITE_TOOLS.has(input.tool)) return
            const args = input.args || {}
            const path = args.filePath || args.path || args.file
            if (typeof path !== "string") return
            if (!path.endsWith(".kuki")) return
            if (path.includes("/.kukicha/")) return // vendored stdlib

            const isTest = path.endsWith("_test.kuki")

            let text
            try {
                text = await readFile(path, "utf8")
            } catch {
                return // file may have been moved/deleted; nothing to lint
            }

            let { errors, warnings } = scan(text)

            // Discard rule is relaxed in test files (onerr discard is sanctioned).
            if (isTest) {
                warnings = warnings.concat(
                    errors.filter((e) => /_ =|_ :=|discard/.test(e.msg)),
                )
                errors = errors.filter((e) => !/_ =|_ :=|discard/.test(e.msg))
            }

            const smell = aliasSmell(text)
            if (smell) warnings.push({ line: 0, text: "(file)", msg: smell })

            if (warnings.length) {
                const note =
                    `\n\n⚠️  Kukicha idiom warnings in ${path}:\n` + fmt(warnings)
                output.output = (output.output || "") + note
            }

            if (errors.length) {
                throw new Error(
                    `Kukicha idiom violations in ${path} — fix before continuing ` +
                        `(these are valid Go but rejected in .kuki per AGENTS.md):\n` +
                        fmt(errors),
                )
            }
        },
    }
}
