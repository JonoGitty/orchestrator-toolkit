#!/usr/bin/env python3
"""
Test suite for Orchestrator Toolkit.
Run with: python -m pytest tests/ -v
"""
import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

# Ensure 'openai' is importable for tests (mocked)
sys.modules.setdefault("openai", MagicMock())

from cloud_agent.cloud_client import _parse_any_plan, _normalize_plan
from config import Config, ConfigManager, get_config_manager
from plugins import PluginManager, BUILTIN_HOOKS


class TestPlanParsing:
    """Test JSON plan parsing and normalization."""

    def test_parse_valid_json_plan(self):
        valid_plan = {
            "name": "test-project",
            "description": "A test project",
            "files": [{"filename": "main.py", "code": "print('Hello')"}],
            "run": "python main.py",
        }
        raw_json = json.dumps(valid_plan)
        parsed = _parse_any_plan(raw_json)
        assert parsed["name"] == "test-project"
        assert len(parsed["files"]) == 1

    def test_parse_malformed_json(self):
        malformed = '{"name": "test", "files": ['
        parsed = _parse_any_plan(malformed)
        assert isinstance(parsed, dict)
        assert "name" in parsed or "files" in parsed

    def test_normalize_plan_minimal(self):
        normalized = _normalize_plan({"name": "test"})
        assert normalized["name"] == "test"
        assert normalized["files"] == []
        assert normalized["description"] == ""
        assert normalized["run"] == ""

    def test_normalize_plan_array(self):
        files = [{"filename": "app.py", "code": "print(1)"}]
        normalized = _normalize_plan(files)
        assert len(normalized["files"]) == 1
        assert normalized["files"][0]["filename"] == "app.py"

    def test_normalize_plan_string(self):
        normalized = _normalize_plan("print('hello')")
        assert normalized["files"][0]["filename"] == "main.py"


class TestConfiguration:
    """Test configuration management."""

    def test_config_loading(self):
        config = get_config_manager().config
        assert isinstance(config, Config)
        assert hasattr(config, "llm")
        assert hasattr(config, "paths")
        assert hasattr(config, "plugins")
        assert hasattr(config, "security")

    def test_config_defaults(self):
        config = Config.from_dict({})
        assert config.llm.model == "gpt-4.1"
        assert config.llm.temperature == 1.0
        assert config.llm.max_retries == 3
        assert config.paths.output_dir == "output"
        assert config.plugins.enabled == []

    def test_config_new_plugin_fields(self):
        config = Config.from_dict({})
        assert config.plugins.disabled == []
        assert config.plugins.discover_entry_points is True

    def test_config_file_loading(self, tmp_path):
        cfg = tmp_path / "config.json"
        cfg.write_text(
            '{"llm": {"model": "claude-sonnet-4-5-20250929"}, "paths": {"output_dir": "out"}}',
            encoding="utf-8",
        )
        manager = ConfigManager(config_file=cfg)
        config = manager._load_config()
        assert config.llm.model == "claude-sonnet-4-5-20250929"
        assert config.paths.output_dir == "out"
        assert config.llm.temperature == 1.0

    def test_config_has_no_legacy_fields(self):
        config = Config.from_dict({})
        assert not hasattr(config, "behavior")
        assert not hasattr(config, "shortcuts")
        d = config.to_dict()
        assert "behavior" not in d
        assert "shortcuts" not in d


class TestPluginManager:
    """Test the plugin system."""

    def test_add_and_fire_hook(self):
        pm = PluginManager()
        results = []
        pm.add_hook("pre_execute", lambda plan, **kw: results.append(plan))
        pm.hook("pre_execute", plan={"name": "test"})
        assert len(results) == 1
        assert results[0]["name"] == "test"

    def test_hook_returns_last_value(self):
        pm = PluginManager()
        pm.add_hook("pre_execute", lambda plan, **kw: {**plan, "modified": True})
        result = pm.hook("pre_execute", plan={"name": "test"})
        assert result["modified"] is True

    def test_custom_hook_auto_registered(self):
        pm = PluginManager()
        pm.add_hook("my_custom_event", lambda **kw: "hello")
        result = pm.hook("my_custom_event")
        assert result == "hello"
        assert "my_custom_event" in pm.get_hook_names()

    def test_register_hook_type_explicit(self):
        pm = PluginManager()
        pm.register_hook_type("skill_to_skill")
        assert "skill_to_skill" in pm.get_hook_names()

    def test_hook_priority_ordering(self):
        pm = PluginManager()
        order = []
        pm.add_hook("pre_execute", lambda plan, **kw: order.append("B"), priority=200)
        pm.add_hook("pre_execute", lambda plan, **kw: order.append("A"), priority=50)
        pm.add_hook("pre_execute", lambda plan, **kw: order.append("C"), priority=100)
        pm.hook("pre_execute", plan={})
        assert order == ["A", "C", "B"]

    def test_register_and_list(self):
        pm = PluginManager()
        pm.register_plugin("test-plugin", "A test plugin")
        plugins = pm.list_plugins()
        assert len(plugins) == 1
        assert plugins[0] == ("test-plugin", "A test plugin")

    def test_register_plugin_rich_metadata(self):
        pm = PluginManager()
        pm.register_plugin(
            "rich-plugin",
            "A rich plugin",
            version="1.2.3",
            author="Test Author",
            dependencies=["dep-a"],
            capabilities=["logging"],
        )
        detail = pm.list_plugins_detailed()
        assert len(detail) == 1
        p = detail[0]
        assert p["name"] == "rich-plugin"
        assert p["version"] == "1.2.3"
        assert p["author"] == "Test Author"
        assert p["dependencies"] == ["dep-a"]
        assert p["capabilities"] == ["logging"]

    def test_duplicate_register_skipped(self):
        pm = PluginManager()
        pm.register_plugin("dup", "first")
        pm.register_plugin("dup", "second")
        assert len(pm.list_plugins()) == 1
        assert pm.list_plugins()[0][1] == "first"

    def test_get_plugin(self):
        pm = PluginManager()
        pm.register_plugin("findme", "I can be found")
        assert pm.get_plugin("findme")["description"] == "I can be found"
        assert pm.get_plugin("nope") is None

    def test_check_dependencies_all_met(self):
        pm = PluginManager()
        pm.register_plugin("base", "base plugin")
        pm.register_plugin("child", "child", dependencies=["base"])
        assert pm.check_dependencies() == []

    def test_check_dependencies_missing(self):
        pm = PluginManager()
        pm.register_plugin("lonely", "needs friend", dependencies=["missing-dep"])
        problems = pm.check_dependencies()
        assert len(problems) == 1
        assert "missing-dep" in problems[0]

    def test_hook_error_does_not_crash(self):
        pm = PluginManager()
        pm.add_hook("pre_execute", lambda plan, **kw: 1 / 0)
        pm.add_hook("pre_execute", lambda plan, **kw: plan)
        result = pm.hook("pre_execute", plan={"name": "test"})
        assert result["name"] == "test"

    def test_builtin_hooks_present(self):
        pm = PluginManager()
        for hook in BUILTIN_HOOKS:
            assert hook in pm.get_hook_names()

    def test_detect_stack_hook(self):
        pm = PluginManager()
        pm.add_hook("detect_stack", lambda files, **kw: "custom-stack")
        result = pm.hook("detect_stack", files=[])
        assert result == "custom-stack"

    def test_build_hooks(self):
        pm = PluginManager()
        calls = []
        pm.add_hook("pre_build", lambda **kw: calls.append(("pre", kw.get("stack"))))
        pm.add_hook("post_build", lambda **kw: calls.append(("post", kw.get("stack"))))
        pm.hook("pre_build", stack="python", project_dir="/tmp", plan={})
        pm.hook("post_build", stack="python", project_dir="/tmp", result={})
        assert calls == [("pre", "python"), ("post", "python")]


class TestSkillManifest:
    """Test skill.json manifest loading."""

    def test_discover_skill_manifest(self, tmp_path):
        skill_dir = tmp_path / "plugins" / "my_skill"
        skill_dir.mkdir(parents=True)
        manifest = {
            "name": "my-skill",
            "version": "1.0.0",
            "description": "A test skill",
            "author": "Test",
            "dependencies": [],
            "capabilities": ["testing"],
        }
        (skill_dir / "skill.json").write_text(json.dumps(manifest), encoding="utf-8")

        pm = PluginManager()
        pm._discover_skill_manifests(tmp_path / "plugins")

        found = pm.get_plugin("my-skill")
        assert found is not None
        assert found["version"] == "1.0.0"
        assert found["capabilities"] == ["testing"]


class TestSkillPacks:
    """Test skill pack scaffolding, installation, and listing."""

    def test_generate_skill_pack_creates_files(self, tmp_path):
        from scaffolds import generate_skill

        generated = generate_skill(
            "my-test-skill",
            description="A test skill",
            author="Tester",
            output_dir=tmp_path,
        )

        pack_dir = tmp_path / "packs" / "my_test_skill"
        assert pack_dir.is_dir()
        assert (pack_dir / "skill.json").exists()
        assert (pack_dir / "CONTEXT.md").exists()
        assert (pack_dir / "hooks.py").exists()
        assert (pack_dir / "skills" / "my_test_skill" / "SKILL.md").exists()
        assert (tmp_path / "tests" / "test_my_test_skill.py").exists()

        # Manifest is valid JSON with correct values
        manifest = json.loads((pack_dir / "skill.json").read_text())
        assert manifest["name"] == "my-test-skill"
        assert manifest["version"] == "0.1.0"
        assert manifest["author"] == "Tester"

        # SKILL.md references the skill name
        skill_src = (pack_dir / "skills" / "my_test_skill" / "SKILL.md").read_text()
        assert "my-test-skill" in skill_src
        assert "A test skill" in skill_src

        # Hooks module has register function
        hooks_src = (pack_dir / "hooks.py").read_text()
        assert 'PLUGIN_NAME = "my-test-skill"' in hooks_src
        assert "def register(manager)" in hooks_src

    def test_generate_skill_returns_paths(self, tmp_path):
        from scaffolds import generate_skill

        generated = generate_skill("cool-skill", output_dir=tmp_path)
        assert "manifest" in generated
        assert "context" in generated
        assert "skill" in generated
        assert "hooks" in generated
        assert "test" in generated

    def test_install_skill_copies_to_claude_skills(self, tmp_path):
        from scaffolds import generate_skill, install_skill

        # Generate a pack
        generate_skill("test-pack", description="Test", output_dir=tmp_path)
        pack_dir = tmp_path / "packs" / "test_pack"

        # Install it
        target_dir = tmp_path / ".claude" / "skills"
        installed = install_skill(pack_dir, target_dir=target_dir)

        assert "test_pack" in installed
        assert (target_dir / "test_pack" / "SKILL.md").exists()
        assert (target_dir / "test_pack" / "CONTEXT.md").exists()

    def test_list_packs(self, tmp_path):
        from scaffolds import generate_skill, list_packs

        generate_skill("pack-a", description="Pack A", output_dir=tmp_path)
        generate_skill("pack-b", description="Pack B", output_dir=tmp_path)

        packs = list_packs(tmp_path / "packs")
        assert len(packs) == 2
        names = {p["name"] for p in packs}
        assert names == {"pack-a", "pack-b"}

    def test_list_packs_empty(self, tmp_path):
        from scaffolds import list_packs

        packs = list_packs(tmp_path / "nonexistent")
        assert packs == []

    def test_slugify_names(self):
        from scaffolds import _slugify

        assert _slugify("my-awesome-skill") == "my_awesome_skill"
        assert _slugify("CamelCase Plugin") == "camelcase_plugin"
        assert _slugify("---weird---") == "weird"
        assert _slugify("") == "my_skill"


class TestArcGISPack:
    """Test the bundled ArcGIS example skill pack."""

    ARCGIS_DIR = Path(__file__).parent.parent / "packs" / "arcgis"

    def test_manifest_exists(self):
        manifest = json.loads((self.ARCGIS_DIR / "skill.json").read_text())
        assert manifest["name"] == "arcgis"
        assert "arcpy" in manifest["capabilities"]

    def test_manifest_lists_all_skills(self):
        manifest = json.loads((self.ARCGIS_DIR / "skill.json").read_text())
        assert "skills/arcgis" in manifest["skills"]
        assert "skills/arcgis-project" in manifest["skills"]
        assert "skills/arcgis-ingest" in manifest["skills"]

    def test_manifest_capabilities(self):
        manifest = json.loads((self.ARCGIS_DIR / "skill.json").read_text())
        for cap in ["network-analyst", "spatial-statistics", "geocoding", "raster", "project-management"]:
            assert cap in manifest["capabilities"]

    def test_context_has_content(self):
        context = (self.ARCGIS_DIR / "CONTEXT.md").read_text()
        assert "arcpy" in context
        assert "SearchCursor" in context
        assert "SpatialReference" in context

    def test_context_has_network_analyst(self):
        context = (self.ARCGIS_DIR / "CONTEXT.md").read_text()
        assert "arcpy.na" in context
        assert "MakeServiceAreaAnalysisLayer" in context
        assert "MakeRouteAnalysisLayer" in context

    def test_context_has_spatial_statistics(self):
        context = (self.ARCGIS_DIR / "CONTEXT.md").read_text()
        assert "HotSpots" in context
        assert "ClustersOutliers" in context
        assert "OrdinaryLeastSquares" in context

    def test_context_has_automation_vs_manual(self):
        context = (self.ARCGIS_DIR / "CONTEXT.md").read_text()
        assert "Automation vs Manual" in context
        assert "Fully scriptable" in context
        assert "Requires ArcGIS Pro UI" in context

    def test_skill_md_exists(self):
        skill = (self.ARCGIS_DIR / "skills" / "arcgis" / "SKILL.md").read_text()
        assert "name: arcgis" in skill
        assert "user-invocable: true" in skill

    def test_arcgis_project_skill_exists(self):
        skill = (self.ARCGIS_DIR / "skills" / "arcgis-project" / "SKILL.md").read_text()
        assert "name: arcgis-project" in skill
        assert "user-invocable: true" in skill

    def test_arcgis_ingest_skill_exists(self):
        skill = (self.ARCGIS_DIR / "skills" / "arcgis-ingest" / "SKILL.md").read_text()
        assert "name: arcgis-ingest" in skill
        assert "user-invocable: true" in skill

    def test_project_template_exists(self):
        template_dir = self.ARCGIS_DIR / "projects" / ".template"
        assert template_dir.is_dir()
        for name in ["BRIEF.md", "DATASETS.md", "PARAMETERS.md", "MATERIALS.md", "NOTES.md"]:
            assert (template_dir / name).exists(), f"Missing template: {name}"

    def test_project_template_has_content(self):
        template_dir = self.ARCGIS_DIR / "projects" / ".template"
        for name in ["BRIEF.md", "DATASETS.md", "PARAMETERS.md", "MATERIALS.md", "NOTES.md"]:
            content = (template_dir / name).read_text()
            assert len(content) > 50, f"Template {name} seems too short"

    def test_arcgis_discover_skill_exists(self):
        skill = (self.ARCGIS_DIR / "skills" / "arcgis-discover" / "SKILL.md").read_text()
        assert "name: arcgis-discover" in skill
        assert "user-invocable: true" in skill

    def test_manifest_lists_discover_skill(self):
        manifest = json.loads((self.ARCGIS_DIR / "skill.json").read_text())
        assert "skills/arcgis-discover" in manifest["skills"]

    def test_manifest_has_new_capabilities(self):
        manifest = json.loads((self.ARCGIS_DIR / "skill.json").read_text())
        for cap in ["data-discovery", "hydrology", "3d-analyst", "lidar", "time-series", "web-gis"]:
            assert cap in manifest["capabilities"], f"Missing capability: {cap}"

    def test_context_has_hydrology(self):
        context = (self.ARCGIS_DIR / "CONTEXT.md").read_text()
        assert "Hydrology" in context
        assert "FlowDirection" in context
        assert "FlowAccumulation" in context
        assert "Watershed" in context

    def test_context_has_3d_analyst(self):
        context = (self.ARCGIS_DIR / "CONTEXT.md").read_text()
        assert "3D Analyst" in context
        assert "LAS" in context
        assert "ClassifyLasGround" in context
        assert "LasDatasetToRaster" in context
        assert "Viewshed" in context

    def test_context_has_time_series(self):
        context = (self.ARCGIS_DIR / "CONTEXT.md").read_text()
        assert "Time-Series" in context
        assert "SpaceTimeCube" in context
        assert "EmergingHotSpotAnalysis" in context

    def test_context_has_dataset_discovery(self):
        context = (self.ARCGIS_DIR / "CONTEXT.md").read_text()
        assert "Dataset Discovery" in context
        assert "suggest_tools" in context
        assert "inventory_gdb" in context

    def test_context_has_expanded_web_gis(self):
        context = (self.ARCGIS_DIR / "CONTEXT.md").read_text()
        assert "Feature layer CRUD" in context
        assert "Portal administration" in context
        assert "Web maps and web apps" in context
        assert "Spatially Enabled DataFrames" in context

    def test_context_has_polygon_to_raster(self):
        context = (self.ARCGIS_DIR / "CONTEXT.md").read_text()
        assert "PolygonToRaster" in context
        assert "FeatureToRaster" in context
        assert "CELL_CENTER" in context

    def test_context_has_map_production(self):
        context = (self.ARCGIS_DIR / "CONTEXT.md").read_text()
        assert "Map Production" in context
        assert "createLayout" in context
        assert "createMapFrame" in context
        assert "SCALE_BAR" in context
        assert "NORTH_ARROW" in context
        assert "LEGEND" in context
        assert "exportToJPEG" in context

    def test_context_has_symbology(self):
        context = (self.ARCGIS_DIR / "CONTEXT.md").read_text()
        assert "UniqueValueRenderer" in context
        assert "GraduatedColorsRenderer" in context
        assert "RasterStretchColorizer" in context
        assert "binary raster" in context.lower()

    def test_context_has_labels(self):
        context = (self.ARCGIS_DIR / "CONTEXT.md").read_text()
        assert "showLabels" in context
        assert "listLabelClasses" in context

    def test_context_has_uk_data_sources(self):
        context = (self.ARCGIS_DIR / "CONTEXT.md").read_text()
        assert "British National Grid" in context
        assert "27700" in context
        assert "Edina Digimap" in context
        assert "Environment Agency" in context or "data.gov.uk" in context
        assert "Natural England" in context
        assert "MAGIC" in context
        assert "Agricultural Land Classification" in context

    def test_context_has_suitability_workflow(self):
        context = (self.ARCGIS_DIR / "CONTEXT.md").read_text()
        assert "Multi-Criteria Site Suitability" in context
        assert "Step 1:" in context
        assert "Step 12:" in context
        assert "study_area" in context
        assert "reclassify_exclusion" in context
        assert "suitability_result" in context

    def test_context_has_suitability_gotchas(self):
        context = (self.ARCGIS_DIR / "CONTEXT.md").read_text()
        assert "Suitability Analysis" in context and "Gotchas" in context
        assert "NODATA" in context
        assert "snapRaster" in context
        assert "check_raster_alignment" in context
        assert "dissolve_option" in context

    def test_manifest_has_suitability_capabilities(self):
        manifest = json.loads((self.ARCGIS_DIR / "skill.json").read_text())
        for cap in ["site-suitability", "uk-planning", "layout-automation",
                     "map-production", "polygon-to-raster", "multi-criteria-analysis"]:
            assert cap in manifest["capabilities"], f"Missing capability: {cap}"

    def test_manifest_version_updated(self):
        manifest = json.loads((self.ARCGIS_DIR / "skill.json").read_text())
        assert manifest["version"] == "0.5.0"

    def test_arcgis_setup_skill_exists(self):
        skill = (self.ARCGIS_DIR / "skills" / "arcgis-setup" / "SKILL.md").read_text()
        assert "name: arcgis-setup" in skill
        assert "user-invocable: true" in skill

    def test_setup_skill_covers_arcgis_detection(self):
        skill = (self.ARCGIS_DIR / "skills" / "arcgis-setup" / "SKILL.md").read_text()
        assert "Find ArcGIS Pro" in skill or "find ArcGIS Pro" in skill
        assert "Registry" in skill or "registry" in skill
        assert "conda" in skill or "Python" in skill

    def test_setup_skill_covers_data_scanning(self):
        skill = (self.ARCGIS_DIR / "skills" / "arcgis-setup" / "SKILL.md").read_text()
        assert "scan_for_gis_data" in skill
        assert ".shp" in skill
        assert ".gdb" in skill
        assert ".asc" in skill
        assert ".aprx" in skill

    def test_setup_skill_covers_brief_matching(self):
        skill = (self.ARCGIS_DIR / "skills" / "arcgis-setup" / "SKILL.md").read_text()
        assert "BRIEF" in skill or "brief" in skill
        assert "MISSING" in skill
        assert "FOUND" in skill

    def test_manifest_lists_setup_skill(self):
        manifest = json.loads((self.ARCGIS_DIR / "skill.json").read_text())
        assert "skills/arcgis-setup" in manifest["skills"]

    def test_manifest_has_setup_capabilities(self):
        manifest = json.loads((self.ARCGIS_DIR / "skill.json").read_text())
        for cap in ["environment-detection", "data-scanning", "brief-matching"]:
            assert cap in manifest["capabilities"], f"Missing capability: {cap}"

    def test_context_has_environment_detection(self):
        context = (self.ARCGIS_DIR / "CONTEXT.md").read_text()
        assert "Environment Detection" in context
        assert "find_arcgis_pro" in context
        assert "winreg" in context
        assert "scan_for_gis_data" in context

    def test_context_has_data_identification(self):
        context = (self.ARCGIS_DIR / "CONTEXT.md").read_text()
        assert "identify_uk_dataset" in context
        assert "match_data_to_brief" in context
        assert "find_arcgis_projects" in context

    def test_context_has_uk_suitability_requirements(self):
        context = (self.ARCGIS_DIR / "CONTEXT.md").read_text()
        assert "UK_SUITABILITY_REQUIREMENTS" in context
        assert "digimap.edina.ac.uk" in context or "Edina Digimap" in context
        assert "magic.defra.gov.uk" in context


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
