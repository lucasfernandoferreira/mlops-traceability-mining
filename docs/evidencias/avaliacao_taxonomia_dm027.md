# Avaliação documental da taxonomia DM-027

Rascunho de IA: 173/180 (96.11%); limiar atendido: True. Aceite científico: falso até confirmação e demais controles.

Concordância com julgamentos de IA; não é concordância humana independente. Cegamento limitado pela ordem estratificada e conhecimento prévio do método.

## Divergências preservadas

- `.github/ISSUE_TEMPLATE/config.yml`: CONFIG → OUTRO. .github/ISSUE_TEMPLATE/config.yml @ ae729bf5942bd4a91e8ab4703ecc0dd9f758d721: blank_issues_enabled e contact_links configuram a abertura de issues e canais comunitários; não parametrizam pipeline de ML, ambiente ou execução de CI. Fonte integral: data/interim/fechamento_dm027/fontes_taxonomia/d7573727e145e6a5cad90f7f0848bd7ab5ec5c05; SHA-256 fcc1f0a340882b1b066bb7f198f3628a9978f9f91742bd117a279fdbd7e25ea2.

- `setup.cfg`: ENV → OUTRO. setup.cfg @ 012fc9c56ef9227a2f9a958b7028b228fabea8f5: O blob contém apenas a seção flake8 com max-line-length e extend-ignore; configura lint, sem metadados de pacote ou dependências. Fonte integral: data/interim/fechamento_dm027/fontes_taxonomia/8dd399ab55bce8a4a1ddfd0c98170f771f6e5c35; SHA-256 0b5263b32955f69f1e4f883bb7620dcd975e0e82907f07899770d9f6a2081dbb.

- `examples/YOLO11-Triton-CPP/CMakeLists.txt`: OUTRO → ENV. examples/YOLO11-Triton-CPP/CMakeLists.txt @ 1bccbacc13c431213c8410ba95088fbc2e32f9d0: CMakeLists define padrão C++, TRITON_CLIENT_DIR e diretórios Protobuf/gRPC; configura construção e dependências do exemplo Triton. Fonte integral: data/interim/fechamento_dm027/fontes_taxonomia/38865cd5398305108842926bfc93b7a4307d36f0; SHA-256 ca78dfcdc02223e5552a8f3e14faa32db956985b50fda26fb7c04200d77b39bc.

- `examples/cpp/LibTorch/CMakeLists.txt`: OUTRO → ENV. examples/cpp/LibTorch/CMakeLists.txt @ 947f80cb81b51ab9a0c2028c701fad42c8128e83: CMakeLists define projeto yolo_libtorch, padrão C++ e find_package(OpenCV); descreve o ambiente de compilação e ligação. Fonte integral: data/interim/fechamento_dm027/fontes_taxonomia/d84bda1b63d315a8b71f6ec393b0cf0bb3b67c27; SHA-256 0da621e1862af8503629c46dcfebf3743c1511ce42a7ac793299b84adcf67fdb.

- `.github/actions/security/trivy/action.yaml`: OUTRO → CI. .github/actions/security/trivy/action.yaml @ 1f6081f13fab4bb69ea3783606b23e2aa11264bc: A action Trivy descreve execução composta de security scanning com setup/cache e etapas de análise; compõe automação de CI apesar de ficar fora de workflows. Fonte integral: data/interim/fechamento_dm027/fontes_taxonomia/d2049d2426e3656d85201b4f71b44cfd01f6ea77; SHA-256 a2fd5375bdfd3cd691501405cc29a150de06286faa5471a29a9816362da50737.

- `examples/cpp/MNN/CMakeLists.txt`: OUTRO → ENV. examples/cpp/MNN/CMakeLists.txt @ 947f80cb81b51ab9a0c2028c701fad42c8128e83: CMakeLists define yolo_mnn, OpenCV e caminhos MNN_INCLUDE_DIR/MNN_LIB_DIR; especifica construção e ligação do exemplo. Fonte integral: data/interim/fechamento_dm027/fontes_taxonomia/36c0ab304659dc05b29980d7215b57b79e3b509e; SHA-256 ac59c51511852e55ea49fdc6b2fcbcfaa022ee226e992387f009e9037f02975e.

- `examples/cpp/OpenVINO/CMakeLists.txt`: OUTRO → ENV. examples/cpp/OpenVINO/CMakeLists.txt @ 947f80cb81b51ab9a0c2028c701fad42c8128e83: CMakeLists usa find_package(OpenCV/OpenVINO), add_executable e target_link_libraries; define dependências e montagem do binário. Fonte integral: data/interim/fechamento_dm027/fontes_taxonomia/08cf6ee0ecd3342684cc10f4fee48ea6d07e9bcc; SHA-256 58398b263df42a93fac6deb7239cf7a60cac53bcbfd4515083b46ca04e1d38bb.

As unidades e regras permanecem intactas. A categoria DATA_META não recebe acerto artificial. O relatório da fase 6 apresenta a matriz e os estratos. Arquivos CMake expressam construção/dependências; ações compostas são automação; nomes config/setup isoladamente podem capturar ferramentas fora do pipeline. Esses mecanismos devem ser discutidos mesmo se a concordância global superar o limiar.
