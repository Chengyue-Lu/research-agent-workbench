from __future__ import annotations

import copy
import importlib.util
import io
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("release_surface", ROOT / ".github/scripts/release_surface.py")
release = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(release)


def command(repo, *args, data=None, env=None):
    result = subprocess.run(["git", "-C", str(repo), *args], input=data, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, env={**os.environ, **(env or {})}, check=False)
    if result.returncode:
        raise AssertionError(result.stderr.decode("utf-8", errors="replace"))
    return result.stdout


def write(repo, path, value):
    target = repo / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(value)


class ReleaseSurfaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.seed_temp = tempfile.TemporaryDirectory(prefix="rwb-surface-seed-")
        cls.seed = Path(cls.seed_temp.name)
        command(cls.seed, "init", "-q", "-b", "main")
        command(cls.seed, "config", "user.name", "Release Fixture")
        command(cls.seed, "config", "user.email", "fixture@example.invalid")
        command(cls.seed, "config", "core.autocrlf", "false")
        write(cls.seed, "old-main-only.txt", b"must disappear\n")
        command(cls.seed, "add", "old-main-only.txt")
        command(cls.seed, "commit", "-qm", "main parent")
        cls.initial_parent = command(cls.seed, "rev-parse", "HEAD").decode().strip()
        command(cls.seed, "checkout", "-qb", "develop")
        cls.policy = {"schema_version": "0.1.0", "policy_id": "rwb-release-surface", "policies": [{
            "version": "1.0.0", "include": [{"path": ".gitattributes", "kind": "file"},
                                            {"path": "src", "kind": "tree"},
                                            {"path": "schemas", "kind": "tree"}],
            "generated": [{"path": "VERSION.json", "generator": "rwb-release-metadata",
                           "version": "1.0.0", "label": "fixture"}]}]}
        write(cls.seed, ".gitattributes", b"* -text\n")
        write(cls.seed, "src/run.py", b"print('frozen source')\n")
        write(cls.seed, "src/nested/data.json", b'{"stable": true}\n')
        write(cls.seed, "tests/private.txt", b"excluded\n")
        write(cls.seed, ".hidden-input", b"excluded too\n")
        for path in (release.TOOL, *release.SCHEMAS.values()):
            write(cls.seed, path, (ROOT / path).read_bytes())
        write(cls.seed, release.POLICY, release.canonical(cls.policy))
        command(cls.seed, "add", ".")
        command(cls.seed, "commit", "-qm", "source")

    @classmethod
    def tearDownClass(cls):
        cls.seed_temp.cleanup()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="rwb-surface-")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.repo = self.base / "repo"
        command(self.base, "clone", "-q", "--no-hardlinks", str(self.seed), str(self.repo))
        command(self.repo, "config", "user.name", "Release Fixture")
        command(self.repo, "config", "user.email", "fixture@example.invalid")
        command(self.repo, "config", "core.autocrlf", "false")
        command(self.repo, "remote", "set-url", "origin", "https://github.com/Example/workbench.git")
        source = command(self.repo, "rev-parse", "HEAD").decode().strip()
        self.expected = {"repository": "Example/workbench", "source": source, "parent": self.initial_parent,
                         "policy_version": "1.0.0", "release_version": "1.0.0", "source_ci": {
                             "repository": "Example/workbench", "sha": source, "workflow": "CI", "run_id": 123,
                             "conclusion": "success", "required_checks": release.REQUIRED_CHECKS}}

    def update_source(self, *, version=None):
        command(self.repo, "add", ".")
        command(self.repo, "commit", "-qm", "fixture update")
        source = command(self.repo, "rev-parse", "HEAD").decode().strip()
        command(self.repo, "update-ref", "refs/remotes/origin/develop", source)
        self.expected["source"] = self.expected["source_ci"]["sha"] = source
        if version:
            self.expected["policy_version"] = version

    def policy_version(self, mutate):
        policy = copy.deepcopy(self.policy)
        following = copy.deepcopy(policy["policies"][-1])
        following["version"] = "2.0.0"
        mutate(following)
        policy["policies"].append(following)
        write(self.repo, release.POLICY, release.canonical(policy))
        self.update_source(version="2.0.0")

    def candidate(self, files, parents=None):
        # Independent Git index plumbing is the oracle for the computed tree ID.
        index = self.base / "candidate-index"
        env = {"GIT_INDEX_FILE": str(index)}
        command(self.repo, "read-tree", "--empty", env=env)
        records = []
        for path, (mode, data) in sorted(files.items()):
            oid = command(self.repo, "hash-object", "-w", "--stdin", data=data).strip()
            records.append(mode.encode() + b" " + oid + b"\t" + path.encode("utf-8") + b"\0")
        command(self.repo, "update-index", "-z", "--index-info", data=b"".join(records), env=env)
        tree = command(self.repo, "write-tree", env=env).decode().strip()
        args = ["commit-tree", tree]
        for parent in parents or [self.expected["parent"]]:
            args += ["-p", parent]
        return command(self.repo, *args, data=b"generated fixture\n").decode().strip(), tree

    def blocked(self, mutate, pattern=None):
        files = release.project(self.repo, self.expected)
        mutate(files)
        candidate, _ = self.candidate(files)
        with self.assertRaisesRegex(release.ReleaseError, pattern or "."):
            release.check(self.repo, self.expected, candidate)

    def test_export_twice_and_git_merge_tree_are_byte_identical(self):
        first, second = self.base / "one", self.base / "two"
        first.mkdir()
        second.mkdir()
        result = release.export(self.repo, self.expected, first)
        self.assertEqual(result, release.export(self.repo, self.expected, second))
        files = release.project(self.repo, self.expected)
        self.assertEqual(release.directory_files(first, files), release.directory_files(second, files))
        candidate, tree = self.candidate(files)
        self.assertEqual(tree, result["tree"])
        self.assertEqual(result, release.check(self.repo, self.expected, candidate, directory=first))
        manifest = json.loads((first / release.MANIFEST).read_bytes())
        self.assertIn("tests/private.txt", manifest["excluded"])
        self.assertNotIn("old-main-only.txt", files)
        self.assertEqual("source_blob", next(x for x in manifest["outputs"] if x["path"] == "src/run.py")["origin"])
        self.assertFalse(result["merge_eligible"])

    def test_two_versions_remove_old_generated_output_and_reject_stale_parent(self):
        v1 = release.project(self.repo, self.expected)
        commit1, _ = self.candidate(v1)
        command(self.repo, "update-ref", "refs/remotes/origin/main", commit1)
        self.policy_version(lambda policy: policy["generated"].__setitem__(0, {
            "path": "metadata/v2.json", "generator": "rwb-release-metadata", "version": "1.0.0", "label": "v2"}))
        with self.assertRaisesRegex(release.ReleaseError, "parent drift"):
            release.project(self.repo, self.expected)
        self.expected["parent"] = commit1
        self.expected["release_version"] = "2.0.0"
        v2 = release.project(self.repo, self.expected)
        self.assertNotIn("VERSION.json", v2)
        candidate, tree = self.candidate(v2)
        self.assertEqual(tree, release.check(self.repo, self.expected, candidate)["tree"])
        v2["VERSION.json"] = v1["VERSION.json"]
        stale, _ = self.candidate(v2)
        with self.assertRaisesRegex(release.ReleaseError, "stale"):
            release.check(self.repo, self.expected, stale)

    def test_synchronized_source_and_manifest_hash_forgery_is_blocked(self):
        def forge(files):
            files["src/run.py"] = "100644", b"print('forged')\n"
            manifest = json.loads(files[release.MANIFEST][1])
            row = next(item for item in manifest["outputs"] if item["path"] == "src/run.py")
            row.update(sha256=release.digest(files["src/run.py"][1]), size=len(files["src/run.py"][1]),
                       blob=release.object_id("blob", files["src/run.py"][1]))
            files[release.MANIFEST] = "100644", release.canonical(manifest)
        self.blocked(forge, "drift")

    def test_extra_hidden_missing_moved_and_mode_drift_are_blocked(self):
        for mutate in (
            lambda f: f.update({".hidden": ("100644", b"hidden")}),
            lambda f: f.pop("src/run.py"),
            lambda f: f.update({"renamed.py": f.pop("src/run.py")}),
            lambda f: f.update({"src/run.py": ("100755", f["src/run.py"][1])}),
            lambda f: f.update({"VERSION.json": ("100644", b"undeclared generator output\n")}),
            lambda f: f.update({"src/run.py": ("100644", f["src/run.py"][1].replace(b"\n", b"\r\n"))}),
        ):
            with self.subTest(mutate=mutate):
                self.blocked(mutate)

    def test_manifest_unknown_reordered_crlf_duplicate_and_forged_exclusions_fail(self):
        def altered(change):
            def mutate(files):
                manifest = json.loads(files[release.MANIFEST][1])
                change(manifest)
                files[release.MANIFEST] = "100644", release.canonical(manifest)
            return mutate
        mutations = [altered(lambda m: m.update(unknown=True)),
                     altered(lambda m: m["excluded"].clear()),
                     altered(lambda m: m["outputs"].reverse()),
                     lambda f: f.update({release.MANIFEST: ("100644", f[release.MANIFEST][1].replace(b"\n", b"\r\n"))}),
                     lambda f: f.update({release.MANIFEST: ("100644", b'{"kind":1,"kind":2}')})]
        for mutate in mutations:
            with self.subTest(mutate=mutate):
                self.blocked(mutate)

    def test_source_and_ci_expectations_cannot_come_from_manifest(self):
        for change in (
            lambda e: e.update(repository="attacker/repo"),
            lambda e: e.update(source="0" * 40),
            lambda e: e.update(source="HEAD"),
            lambda e: e.update(extra="untrusted"),
            lambda e: e["source_ci"].update(sha="0" * 40),
            lambda e: e["source_ci"].update(repository="attacker/repo"),
            lambda e: e["source_ci"].update(required_checks=["governance"]),
            lambda e: e["source_ci"].update(conclusion="failure"),
            lambda e: e.update(release_version="01.0.0"),
            lambda e: e.update(policy_version="9.0.0"),
        ):
            expected = copy.deepcopy(self.expected)
            change(expected)
            with self.subTest(expected=expected), self.assertRaises(release.ReleaseError):
                release.project(self.repo, expected)

    def test_source_must_belong_to_fetched_develop(self):
        command(self.repo, "update-ref", "refs/remotes/origin/develop", self.initial_parent)
        with self.assertRaisesRegex(release.ReleaseError, "Git merge-base"):
            release.project(self.repo, self.expected)

    def test_candidate_must_have_exact_single_main_parent(self):
        files = release.project(self.repo, self.expected)
        for parents in ([self.expected["source"]], [self.expected["parent"], self.expected["source"]]):
            candidate, _ = self.candidate(files, parents)
            with self.assertRaisesRegex(release.ReleaseError, "exactly"):
                release.check(self.repo, self.expected, candidate)
        with self.assertRaisesRegex(release.ReleaseError, "exact commit"):
            release.check(self.repo, self.expected, "HEAD")

    def test_dirty_tracked_and_untracked_source_are_rejected(self):
        path = self.repo / "src/run.py"
        old = path.read_bytes()
        path.write_bytes(b"dirty\n")
        with self.assertRaisesRegex(release.ReleaseError, "dirty"):
            release.project(self.repo, self.expected)
        path.write_bytes(old)
        write(self.repo, ".untracked", b"extra")
        with self.assertRaisesRegex(release.ReleaseError, "dirty"):
            release.project(self.repo, self.expected)

    def test_policy_same_version_drift_is_rejected(self):
        policy = copy.deepcopy(self.policy)
        policy["policies"][0]["generated"] = []
        write(self.repo, release.POLICY, release.canonical(policy))
        self.update_source()
        with self.assertRaisesRegex(release.ReleaseError, "append-only"):
            release.project(self.repo, self.expected)

    def test_policy_history_removal_and_restore_is_rejected(self):
        (self.repo / release.POLICY).unlink()
        self.update_source()
        write(self.repo, release.POLICY, release.canonical(self.policy))
        self.update_source()
        with self.assertRaisesRegex(release.ReleaseError, "removed"):
            release.project(self.repo, self.expected)

    def test_policy_unknown_empty_duplicate_and_unsorted_versions_are_rejected(self):
        for mutate in (lambda p: p.update(unknown=True),
                       lambda p: p["policies"].clear(),
                       lambda p: p["policies"].append(copy.deepcopy(p["policies"][0])),
                       lambda p: p["policies"].insert(0, {**p["policies"][0], "version": "2.0.0"})):
            policy = copy.deepcopy(self.policy)
            mutate(policy)
            write(self.repo, release.POLICY, release.canonical(policy))
            self.update_source()
            with self.subTest(policy=policy), self.assertRaises(release.ReleaseError):
                release.project(self.repo, self.expected)
            command(self.repo, "reset", "--hard", "HEAD^")

    def test_include_missing_duplicate_overlap_and_file_tree_ambiguity_fail(self):
        cases = [({"path": "missing", "kind": "file"},),
                 ({"path": "src", "kind": "file"},),
                 ({"path": "src/run.py", "kind": "tree"},),
                 ({"path": "src/run.py", "kind": "file"},),
                 ({"path": "src", "kind": "tree"},),
                 ({"path": "registry", "kind": "tree"},)]
        for additions in cases:
            self.policy_version(lambda p: p["include"].extend(additions))
            with self.subTest(additions=additions), self.assertRaises(release.ReleaseError):
                release.project(self.repo, self.expected)
            command(self.repo, "reset", "--hard", "HEAD^")

    def test_generated_overlap_reserved_manifest_and_undeclared_generator_fail(self):
        for change in (lambda p: p["generated"][0].update(path="src/run.py"),
                       lambda p: p["generated"].append(copy.deepcopy(p["generated"][0])),
                       lambda p: p["generated"][0].update(path=release.MANIFEST),
                       lambda p: p["generated"][0].update(generator="shell-command"),
                       lambda p: p["generated"][0].update(label="C:/temporary/input"),
                       lambda p: p["generated"][0].update(version="2.0.0")):
            self.policy_version(change)
            with self.subTest(change=change), self.assertRaises(release.ReleaseError):
                release.project(self.repo, self.expected)
            command(self.repo, "reset", "--hard", "HEAD^")

    def test_source_manifest_and_omitted_attributes_are_rejected(self):
        write(self.repo, release.MANIFEST, b"{}\n")
        self.policy_version(lambda p: p["include"].append({"path": release.MANIFEST, "kind": "file"}))
        with self.assertRaisesRegex(release.ReleaseError, "manifest-last"):
            release.project(self.repo, self.expected)
        command(self.repo, "reset", "--hard", "HEAD^")
        self.policy_version(lambda p: p["include"].pop(0))
        with self.assertRaisesRegex(release.ReleaseError, "attributes"):
            release.project(self.repo, self.expected)

    def test_portable_path_attack_matrix(self):
        for path in ("", "/root", "C:/temp", "a\\b", "a/../b", "./a", "a//b", "a/", "a.", "a ",
                     "NUL.txt", "COM1", "lpt9.log", "COM¹", "a/.GIT/config", "a\x00b", "a\nb", "a?", "a*b",
                     "a:b", "a|b", "<a>", 'a"b', "e\u0301.txt", "conin$", "conout$"):
            with self.subTest(path=path), self.assertRaises(release.ReleaseError):
                release.portable(path)
        for paths in (["a", "a"], ["A/x", "a/y"], ["a", "a/b"], ["Straße", "STRASSE"]):
            with self.subTest(paths=paths), self.assertRaises(release.ReleaseError):
                release.paths_unique(paths)
        release.paths_unique([".hidden", "é.txt", "a/x", "a/y", "auxiliary", "com10"])

    def test_git_symlink_gitlink_casefold_and_non_utf8_paths_are_rejected(self):
        original = command(self.repo, "rev-parse", "HEAD").decode().strip()
        oid = command(self.repo, "hash-object", "-w", "--stdin", data=b"target").strip()
        for mode, object_name, path in ((b"120000", oid, b"src/link"),
                                        (b"160000", original.encode(), b"src/submodule"),
                                        (b"100644", oid, b"SRC/other"),
                                        (b"100644", oid, b"src/\xff")):
            record = mode + b" " + object_name + b"\t" + path + b"\0"
            command(self.repo, "update-index", "-z", "--index-info", data=record)
            tree = command(self.repo, "write-tree").decode().strip()
            with self.subTest(path=path), self.assertRaises(release.ReleaseError):
                release.entries(self.repo, tree)
            command(self.repo, "read-tree", "HEAD")

    def test_source_crlf_and_checker_drift_are_rejected(self):
        write(self.repo, "src/run.py", b"converted\r\n")
        self.update_source()
        with self.assertRaisesRegex(release.ReleaseError, "CRLF"):
            release.project(self.repo, self.expected)
        command(self.repo, "reset", "--hard", "HEAD^")
        write(self.repo, release.TOOL, b"print('untrusted generator')\n")
        self.update_source()
        with self.assertRaisesRegex(release.ReleaseError, "trusted checker"):
            release.project(self.repo, self.expected)

    def test_policy_include_escape_is_rejected_during_projection(self):
        self.policy_version(lambda p: p["include"].append({"path": "../outside", "kind": "file"}))
        with self.assertRaisesRegex(release.ReleaseError, "ambiguous path"):
            release.project(self.repo, self.expected)

    def test_generated_prefix_collision_is_rejected_during_projection(self):
        self.policy_version(lambda p: p["generated"][0].update(path="SRC/extra.json"))
        with self.assertRaisesRegex(release.ReleaseError, "casefold"):
            release.project(self.repo, self.expected)

    def test_corrupt_git_blob_bytes_fail_before_projection(self):
        with patch.object(release, "git", return_value=b"corrupt object"):
            with self.assertRaisesRegex(release.ReleaseError, "Git blob integrity"):
                release.blob(self.repo, "0" * 40)

    def test_git_environment_cannot_redirect_repository(self):
        expected = self.expected["source"]
        with patch.dict(os.environ, {"GIT_DIR": str(self.base / "missing"), "GIT_WORK_TREE": str(self.base),
                                     "GIT_CONFIG_COUNT": "1", "GIT_CONFIG_KEY_0": "core.bare", "GIT_CONFIG_VALUE_0": "true"}):
            self.assertEqual(expected, release.git(self.repo, "rev-parse", "HEAD").decode().strip())

    def test_links_and_junctions_in_staging_fail_closed(self):
        output = self.base / "out"
        output.mkdir()
        with patch.object(Path, "is_symlink", return_value=True):
            with self.assertRaisesRegex(release.ReleaseError, "link/junction"):
                release.directory_files(output, {})
        stat_result = type("Reparse", (), {"st_file_attributes": 0x400, "st_mode": 0o40755})()
        with patch.object(Path, "lstat", return_value=stat_result):
            with self.assertRaisesRegex(release.ReleaseError, "link/junction"):
                release.no_links(output)

    def test_independent_merge_result_disagreement_is_blocking(self):
        files = release.project(self.repo, self.expected)
        candidate, _ = self.candidate(files)
        original = release.git
        def drift(repo, *args, **kwargs):
            return b"0" * 40 + b"\n" if args[0] == "merge-tree" else original(repo, *args, **kwargs)
        with patch.object(release, "git", side_effect=drift), self.assertRaisesRegex(release.ReleaseError, "prospective"):
            release.check(self.repo, self.expected, candidate)

    def test_binary_source_and_executable_mode_preserve_bytes(self):
        write(self.repo, "src/binary.bin", b"\xff\x00\r\n")
        write(self.repo, "src/binary-with-nul.bin", b"\x00\r\n")
        command(self.repo, "add", "src/binary.bin")
        command(self.repo, "update-index", "--chmod=+x", "src/run.py")
        command(self.repo, "config", "core.filemode", "false")
        self.update_source()
        files = release.project(self.repo, self.expected)
        self.assertEqual(b"\xff\x00\r\n", files["src/binary.bin"][1])
        self.assertEqual("100755", files["src/run.py"][0])
        candidate, tree = self.candidate(files)
        self.assertEqual(tree, release.check(self.repo, self.expected, candidate)["tree"])

    def test_export_refuses_nonempty_relative_and_checkout_directories(self):
        for path in (Path("relative"), self.repo, self.repo / "src", self.base):
            with self.subTest(path=path), self.assertRaises(release.ReleaseError):
                release.export(self.repo, self.expected, path)

    def test_directory_checks_hidden_empty_directory_and_crlf_drift(self):
        output = self.base / "out"
        output.mkdir()
        release.export(self.repo, self.expected, output)
        files = release.project(self.repo, self.expected)
        candidate, _ = self.candidate(files)
        (output / ".unexpected").mkdir()
        with self.assertRaisesRegex(release.ReleaseError, "unexpected staging"):
            release.check(self.repo, self.expected, candidate, directory=output)
        (output / ".unexpected").rmdir()
        (output / "src/run.py").write_bytes(b"converted\r\n")
        with self.assertRaisesRegex(release.ReleaseError, "working projection"):
            release.check(self.repo, self.expected, candidate, directory=output)

    def test_shallow_remote_and_git_format_prerequisites(self):
        original = release.git
        for arguments, result in ((('rev-parse', '--is-shallow-repository'), b'true\n'),
                                  (('rev-parse', '--show-object-format'), b'sha256\n'),
                                  (('remote', 'get-url', 'origin'), b'https://evil.invalid/repo.git\n')):
            def mocked(repo, *args, **kwargs):
                return result if args == arguments else original(repo, *args, **kwargs)
            with self.subTest(arguments=arguments), patch.object(release, "git", side_effect=mocked), self.assertRaises(release.ReleaseError):
                release.project(self.repo, self.expected)
        command(self.repo, "remote", "set-url", "origin", "git@github.com:Example/workbench.git")
        self.assertTrue(release.project(self.repo, self.expected))

    def test_cli_export_check_and_errors(self):
        expected_file = self.base / "expected.json"
        expected_file.write_bytes(release.canonical(self.expected))
        output = self.base / "out"
        output.mkdir()
        args = ["--repo", str(self.repo), "--expectations", str(expected_file)]
        with redirect_stdout(io.StringIO()) as stdout:
            self.assertEqual(0, release.main(["export", *args, "--output", str(output)]))
        self.assertFalse(json.loads(stdout.getvalue())["merge_eligible"])
        candidate, _ = self.candidate(release.project(self.repo, self.expected))
        with redirect_stdout(io.StringIO()):
            self.assertEqual(0, release.main(["check", *args, "--candidate", candidate]))
        for command_args in (["export", *args], ["check", *args], ["check", *args, "--candidate", "HEAD"]):
            with redirect_stderr(io.StringIO()) as stderr:
                self.assertEqual(1, release.main(command_args))
                self.assertIn("BLOCK", stderr.getvalue())
        expected_file.write_bytes(b"\xff")
        with redirect_stderr(io.StringIO()):
            self.assertEqual(1, release.main(["export", *args, "--output", str(output)]))

    def test_strict_json_duplicate_keys_and_invalid_utf8(self):
        for raw in (b'{"x":1,"x":2}', b"\xff", b"---\nkey: value\n", b"{broken"):
            with self.subTest(raw=raw), self.assertRaises(release.ReleaseError):
                release.parse(raw)

    def test_real_policy_schema_and_no_broad_runtime_or_internal_surface(self):
        policy = release.parse((ROOT / release.POLICY).read_bytes())
        release.validate("policy", policy)
        includes = policy["policies"][0]["include"]
        paths = {item["path"] for item in includes}
        self.assertIn("src/research_workbench", paths)
        self.assertIn("schemas", paths)
        self.assertIn(".gitattributes", paths)
        self.assertTrue(paths.isdisjoint({"registry", ".agents", ".codex", "tests", "work", "docs/STATUS.md"}))
        tracked = set(command(ROOT, "ls-files", "-z").decode().split("\0"))
        tracked.update((release.POLICY, release.TOOL, *release.SCHEMAS.values()))
        selected = set()
        for item in includes:
            matches = {path for path in tracked if path == item["path"]} if item["kind"] == "file" else {
                path for path in tracked if path.startswith(item["path"] + "/")}
            self.assertTrue(matches, item)
            self.assertFalse(selected & matches, item)
            selected |= matches
        for path in selected:
            self.assertFalse(path.startswith(("tests/", "work/", "docs/workstreams/", ".codex/", "skill-lab/")), path)
        governance = json.loads((ROOT / ".github/governance-policy.json").read_text(encoding="utf-8"))
        self.assertEqual("dormant", governance["curated_release_topology"]["activation_state"])


if __name__ == "__main__":
    unittest.main()
