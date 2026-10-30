"""Policy coverage and pinned literal failure paths use the real catalog reader."""

import asyncio
import importlib

import pytest

from twobrain_rec_server.product_analytics.activation_fence import ActivationHold


@pytest.mark.parametrize('case', ['missing', 'duplicate', 'unknown', 'policy'])
def test_retention_policy_fails_before_catalog(monkeypatch, case):
    module = importlib.import_module('twobrain_rec_server.product_analytics.local_retention')
    if case == 'policy':
        monkeypatch.setattr(module, 'retention_rule', lambda _: None)
    else:
        categories = dict(module.LEVEL_RETENTION_CATEGORIES)
        values = list(categories['attribution_profiles'])
        if case == 'missing':
            values.pop()
        else:
            values.append(values[0] if case == 'duplicate' else 'synthetic_unknown')
        categories['attribution_profiles'] = tuple(values)
        monkeypatch.setattr(module, 'LEVEL_RETENTION_CATEGORIES', categories)
    with pytest.raises(ActivationHold, match='retention_catalog'):
        asyncio.run(module.local_retention_database_catalog(None))


@pytest.mark.parametrize('case', ['missing', 'duplicate', 'wrong_tag', 'outside_upgrade', 'disconnected', 'call_args', 'tag_case', 'registry_missing', 'registry_tag'])
def test_function_literal_must_be_unambiguous(monkeypatch, case):
    module = importlib.import_module('twobrain_rec_server.product_analytics.local_retention')
    assert len(module._expected_bodies()) == 8
    original = module.Path.read_text
    def changed(path, *args, **kwargs):
        value = original(path, *args, **kwargs)
        if case == 'disconnected' and path.name == '0100_billing_purchases.py':
            return value.replace('    _install_policies()', '    pass')
        if case == 'call_args' and path.name == '0100_billing_purchases.py':
            return value.replace('    _install_policies()', '    _install_policies(1)')
        if case == 'tag_case' and path.name == '0079_summary_state_versions.py':
            return value.replace('        $fn$', '        $FN$')
        if path.name == '0107_billing_registry.py':
            if case == 'registry_missing':
                return value.replace('CREATE FUNCTION rec_registry_history_guard()', 'SELECT')
            if case == 'registry_tag':
                return value.replace('END $$', 'END $different$')
        if path.name == '0106_activation_milestones.py':
            if case == 'missing':
                return value.replace('CREATE FUNCTION rec_activation_decision_immutable()', 'SELECT')
            if case == 'duplicate':
                return value + '\n' + value[value.index('def upgrade():'):value.index('def downgrade():')]
            if case == 'wrong_tag':
                return value.replace('END $$;', 'END $different$;')
            if case == 'outside_upgrade':
                return value.replace('def upgrade():', 'def synthetic_unrelated():')
        return value
    monkeypatch.setattr(module.Path, 'read_text', changed)
    with pytest.raises(ActivationHold, match='retention_catalog'):
        module._expected_bodies()
