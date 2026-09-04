"""
DADOS USADOS SOMENTE PARA TESTES E REFERENCIA
Conjunto de dados de amostra com esquema idêntico ao retornado pela API oficial do Portal da Transparência (/cartoes).
Ano de Referência: 2026.
Permite executar o pipeline de ponta a ponta sem necessidade de chave de API externa.
"""

from typing import List, Dict, Any

SAMPLE_CARTOES_DATA: List[Dict[str, Any]] = [
    {
        "id": 100001,
        "mesExtrato": "202601",
        "dataTransacao": "12/01/2026",
        "valorTransacao": "4.850,00",
        "tipoCartao": {"codigo": 1, "descricao": "CPGF - Cartão de Pagamento do Governo Federal"},
        "estabelecimento": {"nome": "HOTEL NACIONAL DE BRASILIA LTDA", "cgc": "02.***.***/0001-10"},
        "portador": {"nome": "CARLOS EDUARDO PEREIRA", "cpf": "***.452.189-**"},
        "unidadeGestora": {"codigo": "20001", "nome": "GABINETE DE SEGURANCA INSTITUCIONAL"},
        "orgaoVinculado": {"codigo": "20000", "nome": "PRESIDENCIA DA REPUBLICA"},
        "orgaoSuperior": {"codigo": "20000", "nome": "PRESIDENCIA DA REPUBLICA"}
    },
    {
        "id": 100002,
        "mesExtrato": "202601",
        "dataTransacao": "15/01/2026",
        "valorTransacao": "1.230,50",
        "tipoCartao": {"codigo": 1, "descricao": "CPGF - Cartão de Pagamento do Governo Federal"},
        "estabelecimento": {"nome": "AUTO POSTO ALVORADA COMERCIO DE COMBUSTIVEIS", "cgc": "08.***.***/0001-44"},
        "portador": {"nome": "FERNANDA LIMA SOUZA", "cpf": "***.819.340-**"},
        "unidadeGestora": {"codigo": "30001", "nome": "DIRETORIA DE LOGISTICA"},
        "orgaoVinculado": {"codigo": "30000", "nome": "MINISTERIO DA JUSTICA E SEGURANCA PUBLICA"},
        "orgaoSuperior": {"codigo": "30000", "nome": "MINISTERIO DA JUSTICA E SEGURANCA PUBLICA"}
    },
    {
        "id": 100003,
        "mesExtrato": "202601",
        "dataTransacao": "18/01/2026",
        "valorTransacao": "15.980,00",
        "tipoCartao": {"codigo": 1, "descricao": "CPGF - Cartão de Pagamento do Governo Federal"},
        "estabelecimento": {"nome": "COMPANHIA AEREA LATAM BRASIL", "cgc": "02.***.***/0001-00"},
        "portador": {"nome": "MARCELO SILVEIRA RAMOS", "cpf": "***.124.987-**"},
        "unidadeGestora": {"codigo": "40001", "nome": "SECRETARIA DE ASSUNTOS INTERNACIONAIS"},
        "orgaoVinculado": {"codigo": "40000", "nome": "MINISTERIO DAS RELACOES EXTERIORES"},
        "orgaoSuperior": {"codigo": "40000", "nome": "MINISTERIO DAS RELACOES EXTERIORES"}
    },
    {
        "id": 100004,
        "mesExtrato": "202601",
        "dataTransacao": "22/01/2026",
        "valorTransacao": "345,90",
        "tipoCartao": {"codigo": 1, "descricao": "CPGF - Cartão de Pagamento do Governo Federal"},
        "estabelecimento": {"nome": "PAPELARIA E COPIADORA MODELO", "cgc": "14.***.***/0002-88"},
        "portador": {"nome": "JULIANA COSTA RIBEIRO", "cpf": "***.662.331-**"},
        "unidadeGestora": {"codigo": "26001", "nome": "SECRETARIA DE EDUCACAO BASICA"},
        "orgaoVinculado": {"codigo": "26000", "nome": "MINISTERIO DA EDUCACAO"},
        "orgaoSuperior": {"codigo": "26000", "nome": "MINISTERIO DA EDUCACAO"}
    },
    {
        "id": 100005,
        "mesExtrato": "202601",
        "dataTransacao": "29/01/2026",
        "valorTransacao": "28.500,00",
        "tipoCartao": {"codigo": 1, "descricao": "CPGF - Cartão de Pagamento do Governo Federal"},
        "estabelecimento": {"nome": "SERVICOS DE TECNOLOGIA E NUVEM BRASIL", "cgc": "33.***.***/0001-99"},
        "portador": {"nome": "RODRIGO MARTINS DIAS", "cpf": "***.998.412-**"},
        "unidadeGestora": {"codigo": "53001", "nome": "DEPARTAMENTO DE TRANSFORMACAO DIGITAL"},
        "orgaoVinculado": {"codigo": "53000", "nome": "MINISTERIO DA GESTAO E DA INOVACAO EM SERVICOS PUBLICOS"},
        "orgaoSuperior": {"codigo": "53000", "nome": "MINISTERIO DA GESTAO E DA INOVACAO EM SERVICOS PUBLICOS"}
    },
    {
        "id": 100006,
        "mesExtrato": "202602",
        "dataTransacao": "05/02/2026",
        "valorTransacao": "5.620,00",
        "tipoCartao": {"codigo": 1, "descricao": "CPGF - Cartão de Pagamento do Governo Federal"},
        "estabelecimento": {"nome": "HOTEL NACIONAL DE BRASILIA LTDA", "cgc": "02.***.***/0001-10"},
        "portador": {"nome": "CARLOS EDUARDO PEREIRA", "cpf": "***.452.189-**"},
        "unidadeGestora": {"codigo": "20001", "nome": "GABINETE DE SEGURANCA INSTITUCIONAL"},
        "orgaoVinculado": {"codigo": "20000", "nome": "PRESIDENCIA DA REPUBLICA"},
        "orgaoSuperior": {"codigo": "20000", "nome": "PRESIDENCIA DA REPUBLICA"}
    },
    {
        "id": 100007,
        "mesExtrato": "202602",
        "dataTransacao": "10/02/2026",
        "valorTransacao": "980,40",
        "tipoCartao": {"codigo": 1, "descricao": "CPGF - Cartão de Pagamento do Governo Federal"},
        "estabelecimento": {"nome": "RESTAURANTE E CHURRASCARIA DO VALE", "cgc": "05.***.***/0001-23"},
        "portador": {"nome": "FERNANDA LIMA SOUZA", "cpf": "***.819.340-**"},
        "unidadeGestora": {"codigo": "30001", "nome": "DIRETORIA DE LOGISTICA"},
        "orgaoVinculado": {"codigo": "30000", "nome": "MINISTERIO DA JUSTICA E SEGURANCA PUBLICA"},
        "orgaoSuperior": {"codigo": "30000", "nome": "MINISTERIO DA JUSTICA E SEGURANCA PUBLICA"}
    },
    {
        "id": 100008,
        "mesExtrato": "202602",
        "dataTransacao": "14/02/2026",
        "valorTransacao": "22.340,00",
        "tipoCartao": {"codigo": 1, "descricao": "CPGF - Cartão de Pagamento do Governo Federal"},
        "estabelecimento": {"nome": "COMPANHIA AEREA GOL LINHAS AEREAS", "cgc": "07.***.***/0001-88"},
        "portador": {"nome": "MARCELO SILVEIRA RAMOS", "cpf": "***.124.987-**"},
        "unidadeGestora": {"codigo": "40001", "nome": "SECRETARIA DE ASSUNTOS INTERNACIONAIS"},
        "orgaoVinculado": {"codigo": "40000", "nome": "MINISTERIO DAS RELACOES EXTERIORES"},
        "orgaoSuperior": {"codigo": "40000", "nome": "MINISTERIO DAS RELACOES EXTERIORES"}
    },
    {
        "id": 100009,
        "mesExtrato": "202602",
        "dataTransacao": "20/02/2026",
        "valorTransacao": "1.450,00",
        "tipoCartao": {"codigo": 1, "descricao": "CPGF - Cartão de Pagamento do Governo Federal"},
        "estabelecimento": {"nome": "AUTO POSTO ALVORADA COMERCIO DE COMBUSTIVEIS", "cgc": "08.***.***/0001-44"},
        "portador": {"nome": "PATRICIA GOMES BARROS", "cpf": "***.331.774-**"},
        "unidadeGestora": {"codigo": "36001", "nome": "DEPARTAMENTO DE INFRAESTRUTURA EM SAUDE"},
        "orgaoVinculado": {"codigo": "36000", "nome": "MINISTERIO DA SAUDE"},
        "orgaoSuperior": {"codigo": "36000", "nome": "MINISTERIO DA SAUDE"}
    },
    {
        "id": 100010,
        "mesExtrato": "202602",
        "dataTransacao": "27/02/2026",
        "valorTransacao": "67.890,00",  # Valor atípico / anomalia para teste de detecção
        "tipoCartao": {"codigo": 1, "descricao": "CPGF - Cartão de Pagamento do Governo Federal"},
        "estabelecimento": {"nome": "GLOBAL SECURITY EQUIPAMENTOS ESPECIAIS", "cgc": "19.***.***/0001-52"},
        "portador": {"nome": "CARLOS EDUARDO PEREIRA", "cpf": "***.452.189-**"},
        "unidadeGestora": {"codigo": "20001", "nome": "GABINETE DE SEGURANCA INSTITUCIONAL"},
        "orgaoVinculado": {"codigo": "20000", "nome": "PRESIDENCIA DA REPUBLICA"},
        "orgaoSuperior": {"codigo": "20000", "nome": "PRESIDENCIA DA REPUBLICA"}
    },
    {
        "id": 100011,
        "mesExtrato": "202603",
        "dataTransacao": "02/03/2026",
        "valorTransacao": "3.120,00",
        "tipoCartao": {"codigo": 1, "descricao": "CPGF - Cartão de Pagamento do Governo Federal"},
        "estabelecimento": {"nome": "WINDSOR PLAZA HOTEL BRASILIA", "cgc": "09.***.***/0001-12"},
        "portador": {"nome": "FERNANDA LIMA SOUZA", "cpf": "***.819.340-**"},
        "unidadeGestora": {"codigo": "30001", "nome": "DIRETORIA DE LOGISTICA"},
        "orgaoVinculado": {"codigo": "30000", "nome": "MINISTERIO DA JUSTICA E SEGURANCA PUBLICA"},
        "orgaoSuperior": {"codigo": "30000", "nome": "MINISTERIO DA JUSTICA E SEGURANCA PUBLICA"}
    },
    {
        "id": 100012,
        "mesExtrato": "202603",
        "dataTransacao": "08/03/2026",
        "valorTransacao": "18.400,00",
        "tipoCartao": {"codigo": 1, "descricao": "CPGF - Cartão de Pagamento do Governo Federal"},
        "estabelecimento": {"nome": "COMPANHIA AEREA LATAM BRASIL", "cgc": "02.***.***/0001-00"},
        "portador": {"nome": "MARCELO SILVEIRA RAMOS", "cpf": "***.124.987-**"},
        "unidadeGestora": {"codigo": "40001", "nome": "SECRETARIA DE ASSUNTOS INTERNACIONAIS"},
        "orgaoVinculado": {"codigo": "40000", "nome": "MINISTERIO DAS RELACOES EXTERIORES"},
        "orgaoSuperior": {"codigo": "40000", "nome": "MINISTERIO DAS RELACOES EXTERIORES"}
    },
    {
        "id": 100013,
        "mesExtrato": "202604",
        "dataTransacao": "14/04/2026",
        "valorTransacao": "2.890,75",
        "tipoCartao": {"codigo": 1, "descricao": "CPGF - Cartão de Pagamento do Governo Federal"},
        "estabelecimento": {"nome": "KALUNGA COMERCIO E INDUSTRIA GRAFICA", "cgc": "43.***.***/0001-30"},
        "portador": {"nome": "JULIANA COSTA RIBEIRO", "cpf": "***.662.331-**"},
        "unidadeGestora": {"codigo": "26001", "nome": "SECRETARIA DE EDUCACAO BASICA"},
        "orgaoVinculado": {"codigo": "26000", "nome": "MINISTERIO DA EDUCACAO"},
        "orgaoSuperior": {"codigo": "26000", "nome": "MINISTERIO DA EDUCACAO"}
    },
    {
        "id": 100014,
        "mesExtrato": "202605",
        "dataTransacao": "20/05/2026",
        "valorTransacao": "8.750,00",
        "tipoCartao": {"codigo": 1, "descricao": "CPGF - Cartão de Pagamento do Governo Federal"},
        "estabelecimento": {"nome": "ALUGA VEICULOS E FROTAS RENT A CAR", "cgc": "17.***.***/0001-65"},
        "portador": {"nome": "PATRICIA GOMES BARROS", "cpf": "***.331.774-**"},
        "unidadeGestora": {"codigo": "36001", "nome": "DEPARTAMENTO DE INFRAESTRUTURA EM SAUDE"},
        "orgaoVinculado": {"codigo": "36000", "nome": "MINISTERIO DA SAUDE"},
        "orgaoSuperior": {"codigo": "36000", "nome": "MINISTERIO DA SAUDE"}
    },
    {
        "id": 100015,
        "mesExtrato": "202606",
        "dataTransacao": "26/06/2026",
        "valorTransacao": "1.180,00",
        "tipoCartao": {"codigo": 1, "descricao": "CPGF - Cartão de Pagamento do Governo Federal"},
        "estabelecimento": {"nome": "AUTO POSTO ALVORADA COMERCIO DE COMBUSTIVEIS", "cgc": "08.***.***/0001-44"},
        "portador": {"nome": "CARLOS EDUARDO PEREIRA", "cpf": "***.452.189-**"},
        "unidadeGestora": {"codigo": "20001", "nome": "GABINETE DE SEGURANCA INSTITUCIONAL"},
        "orgaoVinculado": {"codigo": "20000", "nome": "PRESIDENCIA DA REPUBLICA"},
        "orgaoSuperior": {"codigo": "20000", "nome": "PRESIDENCIA DA REPUBLICA"}
    },
    {
        "id": 100016,
        "mesExtrato": "202607",
        "dataTransacao": "11/07/2026",
        "valorTransacao": "12.450,00",
        "tipoCartao": {"codigo": 1, "descricao": "CPGF - Cartão de Pagamento do Governo Federal"},
        "estabelecimento": {"nome": "COMPANHIA AEREA GOL LINHAS AEREAS", "cgc": "07.***.***/0001-88"},
        "portador": {"nome": "MARCELO SILVEIRA RAMOS", "cpf": "***.124.987-**"},
        "unidadeGestora": {"codigo": "40001", "nome": "SECRETARIA DE ASSUNTOS INTERNACIONAIS"},
        "orgaoVinculado": {"codigo": "40000", "nome": "MINISTERIO DAS RELACOES EXTERIORES"},
        "orgaoSuperior": {"codigo": "40000", "nome": "MINISTERIO DAS RELACOES EXTERIORES"}
    },
    {
        "id": 100017,
        "mesExtrato": "202608",
        "dataTransacao": "18/08/2026",
        "valorTransacao": "31.200,00",
        "tipoCartao": {"codigo": 1, "descricao": "CPGF - Cartão de Pagamento do Governo Federal"},
        "estabelecimento": {"nome": "SERVICOS DE TECNOLOGIA E NUVEM BRASIL", "cgc": "33.***.***/0001-99"},
        "portador": {"nome": "RODRIGO MARTINS DIAS", "cpf": "***.998.412-**"},
        "unidadeGestora": {"codigo": "53001", "nome": "DEPARTAMENTO DE TRANSFORMACAO DIGITAL"},
        "orgaoVinculado": {"codigo": "53000", "nome": "MINISTERIO DA GESTAO E DA INOVACAO EM SERVICOS PUBLICOS"},
        "orgaoSuperior": {"codigo": "53000", "nome": "MINISTERIO DA GESTAO E DA INOVACAO EM SERVICOS PUBLICOS"}
    }
]


def get_sample_cartoes() -> List[Dict[str, Any]]:
    """Retorna a lista de transações de amostra com dados de 2026."""
    return SAMPLE_CARTOES_DATA
