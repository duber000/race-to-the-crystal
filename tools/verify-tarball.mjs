#!/usr/bin/env node
'use strict';

/**
 * tools/verify-tarball.mjs — verify a vendored npm tarball against the
 * registry's published integrity hash before committing it as a vendored
 * frontend asset.
 *
 * town-builder's convention (see its AGENTS.md / SECURITY_REVIEW.md): any
 * asset vendored into the repo from npm is checked against the
 * registry-published hash first, so a compromised CDN edge or a poisoned
 * mirror cannot slip a modified build into the repo. This is the same
 * check, runnable before `git add`.
 *
 * Usage:
 *   node tools/verify-tarball.mjs <pkg>@<version> [path/to/package.tgz]
 *
 * With no local file: downloads the registry tarball to a temp file and
 * verifies it. With a local file: verifies that file (e.g. one you already
 * downloaded). Prints the registry's dist.integrity and dist.tarball URL
 * either way, and exits non-zero on mismatch.
 *
 * Registry defaults to https://registry.npmjs.org; override with
 * NPM_REGISTRY=http://localhost:4873 (e.g. a local Verdaccio).
 */

import { createHash } from 'node:crypto';
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

const args = process.argv.slice(2);
if (args.length < 1 || args.includes('--help') || args.includes('-h')) {
    console.error('Usage: node tools/verify-tarball.mjs <pkg>@<version> [path/to/package.tgz]');
    process.exit(2);
}

const spec = args[0];
const localPath = args[1];
const at = spec.lastIndexOf('@');
const name = at > 0 ? spec.slice(0, at) : '';
const version = at > 0 ? spec.slice(at + 1) : '';
if (!name || !version) {
    console.error(`error: expected <pkg>@<version>, got "${spec}"`);
    process.exit(2);
}

const registry = (process.env.NPM_REGISTRY ?? 'https://registry.npmjs.org').replace(/\/$/, '');
// Scoped packages need their slash percent-encoded in the metadata URL.
const metaUrl = `${registry}/${name.replace('/', '%2f')}/${version}`;

function parseIntegrity(integrity) {
    // Subresource Integrity format: "sha512-<base64>" (usually one token).
    const [algoHint, ...rest] = integrity.split('-');
    return { algorithm: algoHint.toLowerCase(), base64: rest.join('-') };
}

function sriEqual(expected, actualBase64) {
    // Constant-time compare of equal-length strings via Buffer compare.
    const a = Buffer.from(expected, 'base64');
    const b = Buffer.from(actualBase64, 'base64');
    return a.length === b.length && a.equals(b);
}

async function main() {
    console.log(`registry:  ${registry}`);
    console.log(`package:   ${name}@${version}`);

    const metaRes = await fetch(metaUrl, { headers: { accept: 'application/json' } });
    if (!metaRes.ok) {
        console.error(`error: registry metadata fetch failed: HTTP ${metaRes.status} from ${metaUrl}`);
        process.exit(1);
    }
    const meta = await metaRes.json();
    const dist = meta?.dist;
    if (!dist?.integrity && !dist?.shasum) {
        console.error('error: registry metadata has no dist.integrity or dist.shasum');
        process.exit(1);
    }
    console.log(`tarball:   ${dist.tarball}`);
    console.log(`integrity: ${dist.integrity ?? '(none — using legacy sha1 shasum)'}`);
    if (dist.shasum) console.log(`shasum:    ${dist.shasum}`);

    // Obtain the bytes to verify: the local file, or the registry tarball.
    let tarballPath = localPath;
    let tempDir = null;
    if (!tarballPath) {
        const res = await fetch(dist.tarball);
        if (!res.ok) {
            console.error(`error: tarball download failed: HTTP ${res.status} from ${dist.tarball}`);
            process.exit(1);
        }
        const body = Buffer.from(await res.arrayBuffer());
        tempDir = mkdtempSync(join(tmpdir(), 'verify-tarball-'));
        tarballPath = join(tempDir, 'package.tgz');
        writeFileSync(tarballPath, body);
    }

    const bytes = readFileSync(tarballPath);
    let ok = false;
    if (dist.integrity) {
        for (const token of dist.integrity.split(/\s+/).filter(Boolean)) {
            const { algorithm, base64 } = parseIntegrity(token);
            const actual = createHash(algorithm).update(bytes).digest('base64');
            const match = sriEqual(base64, actual);
            console.log(`${algorithm}: ${match ? 'MATCH' : 'MISMATCH'}`);
            if (match) ok = true;
        }
    } else {
        // Legacy packages: dist.shasum is sha1 hex.
        const actual = createHash('sha1').update(bytes).digest('hex');
        ok = actual === dist.shasum;
        console.log(`sha1: ${ok ? 'MATCH' : `MISMATCH (got ${actual})`}`);
    }

    if (tempDir) rmSync(tempDir, { recursive: true, force: true });

    if (!ok) {
        console.error('\nFAIL — tarball does not match the registry-published hash. Do not vendor this file.');
        process.exit(1);
    }
    console.log('\nOK — tarball matches the registry-published hash.');
}

main().catch((err) => {
    console.error(`error: ${err.message}`);
    process.exit(1);
});
