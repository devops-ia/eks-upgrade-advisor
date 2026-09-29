## [1.0.2](https://github.com/devops-ia/eks-upgrade-advisor/compare/v1.0.1...v1.0.2) (2026-09-29)


### Bug Fixes

* harden Docker image and rewrite LLM prompt in English ([08116cd](https://github.com/devops-ia/eks-upgrade-advisor/commit/08116cd7df29d855e4e2816ed240b497b07424bc))
* pluto checksum verification downloaded a mismatched filename ([54cc3db](https://github.com/devops-ia/eks-upgrade-advisor/commit/54cc3db046b21466b3d15bd61275609be35f2b7f))
* smoke test never actually ran bash ([d63605f](https://github.com/devops-ia/eks-upgrade-advisor/commit/d63605fc73e271823769744bf30d3263b2dd5e94))

## [1.0.1](https://github.com/devops-ia/eks-upgrade-advisor/compare/v1.0.0...v1.0.1) (2026-09-29)


### Bug Fixes

* pin pluto to an existing release (v5.24.1) ([9351641](https://github.com/devops-ia/eks-upgrade-advisor/commit/9351641239daf561e614fdad5ea0a36421d6ec47))

# 1.0.0 (2026-09-29)


### Bug Fixes

* resolve ruff/mypy CI failures and skip auto-assign for dependabot ([6a8f10e](https://github.com/devops-ia/eks-upgrade-advisor/commit/6a8f10e3c8930821488b081d98eb2b80553aa7c4))
* resolve subprocess binaries to absolute paths (bandit B607) ([2738d21](https://github.com/devops-ia/eks-upgrade-advisor/commit/2738d214f4bf030db7289a96b1760fa3fdd3cd90))
* silence bandit B701 with justification, not by enabling HTML escaping ([1b80ba9](https://github.com/devops-ia/eks-upgrade-advisor/commit/1b80ba9bb0714681720f8c0f5397f0ac31cf9b38))


### Features

* scaffold eks-upgrade-advisor CLI ([b63838d](https://github.com/devops-ia/eks-upgrade-advisor/commit/b63838de85e214aa3e33c2fb99fad1827f915fec))
