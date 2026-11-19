from scripts.check_distribution import check, HELPERS


def test_source_package_is_distinguished_from_private_local_package(tmp_path):
    # Reproduces the user's source-only extraction, without installing any dependencies.
    for name in HELPERS:
        path=tmp_path/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text('helper')
    source=check(tmp_path)
    assert source['ok'] and source['mode']=='source checkout'
    local=check(tmp_path,local=True)
    assert not local['ok']
    assert 'web/dist/index.html' in local['missing']
    assert local['data_directory']=='data/exploratory_snapshots'
    assert len([p for p in local['missing'] if p.startswith('model_registry/')])==6
