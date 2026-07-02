from app.services.content_policy import ContentPolicyService


def test_content_policy_keeps_substantive_article_types() -> None:
    service = ContentPolicyService()

    assert service.is_substantive_fields(
        title="A perspective on neural circuit computation",
        article_type="Perspective",
    )
    assert service.is_substantive_fields(
        title="Large-scale cortical dynamics during memory retrieval",
        article_type="Research Article",
    )


def test_content_policy_excludes_non_substantive_types_and_titles() -> None:
    service = ContentPolicyService()

    assert not service.is_substantive_fields(
        title="Previewing the next wave of connectomics",
        article_type="Preview",
    )
    assert not service.is_substantive_fields(
        title="Correction to: Large-scale cortical dynamics during memory retrieval",
        article_type="Article",
    )


def test_content_policy_excludes_blocked_lifeline_article() -> None:
    service = ContentPolicyService()

    assert not service.is_substantive_fields(
        title="Lifeline",
        article_type="Article",
        doi="https://doi.org/10.1016/S1474-4422(26)00210-3",
    )
    assert not service.is_substantive_fields(
        title="Lifeline",
        article_type="Article",
    )
    assert service.is_substantive_fields(
        title="Lifeline",
        article_type="Article",
        doi="10.1016/example-other",
    )
