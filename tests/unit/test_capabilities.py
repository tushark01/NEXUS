"""Tests for the capability-based security system."""

import pytest

from nexus.core.errors import CapabilityDeniedError
from nexus.security.capabilities import (
    Capability,
    CapabilityEnforcer,
    CapabilityGrant,
)


class TestCapabilityEnforcer:
    def test_default_grants(self):
        enforcer = CapabilityEnforcer()
        # All skills should have LLM_INVOKE and MEMORY_READ by default
        assert enforcer.check("any_skill", Capability.LLM_INVOKE)
        assert enforcer.check("any_skill", Capability.MEMORY_READ)

    def test_grant_and_check(self):
        enforcer = CapabilityEnforcer()
        enforcer.grant("my_skill", [CapabilityGrant(capability=Capability.FILE_READ)])
        assert enforcer.check("my_skill", Capability.FILE_READ)

    def test_denied_capability(self):
        enforcer = CapabilityEnforcer()
        with pytest.raises(CapabilityDeniedError):
            enforcer.check("my_skill", Capability.SHELL_EXECUTE)

    def test_path_constraint(self):
        enforcer = CapabilityEnforcer()
        enforcer.grant(
            "my_skill",
            [CapabilityGrant(
                capability=Capability.FILE_READ,
                constraints={"paths": ["/tmp/*"]},
            )],
        )
        # Should pass with matching path
        assert enforcer.check("my_skill", Capability.FILE_READ, {"path": "/tmp/file.txt"})

        # Should fail with non-matching path
        with pytest.raises(CapabilityDeniedError):
            enforcer.check("my_skill", Capability.FILE_READ, {"path": "/etc/passwd"})

    def test_domain_constraint(self):
        enforcer = CapabilityEnforcer()
        enforcer.grant(
            "web_skill",
            [CapabilityGrant(
                capability=Capability.NETWORK_HTTP,
                constraints={"domains": ["api.example.com"]},
            )],
        )
        assert enforcer.check("web_skill", Capability.NETWORK_HTTP, {"domain": "api.example.com"})

        with pytest.raises(CapabilityDeniedError):
            enforcer.check("web_skill", Capability.NETWORK_HTTP, {"domain": "evil.com"})

    def test_get_grants(self):
        enforcer = CapabilityEnforcer()
        enforcer.grant("s1", [CapabilityGrant(capability=Capability.FILE_WRITE)])
        grants = enforcer.get_grants("s1")
        caps = {g.capability for g in grants}
        assert Capability.FILE_WRITE in caps
        assert Capability.LLM_INVOKE in caps  # default
