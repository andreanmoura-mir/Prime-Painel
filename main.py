from services.robo_escalados import RoboSiannet
from services.robo_performance import RoboPerformance
from services.robo_telemetria import RoboTelemetria
from services.robo_eventos_viagens import RoboEventosViagens


def executar_robo(nome, classe_robo, metodo_extracao):
    """Executa um robô isoladamente e sempre tenta fechar seu navegador."""
    bot = None

    print("\n" + "=" * 60)
    print(f"INICIANDO: {nome}")
    print("=" * 60)

    try:
        bot = classe_robo()
        bot.login_siannet()

        resultado = getattr(bot, metodo_extracao)()

        print(f"\n{nome}: EXTRAÇÃO CONCLUÍDA!")
        print(f"Resultado: {resultado}")

        return {
            "nome": nome,
            "status": "SUCESSO",
            "resultado": resultado,
            "erro": None
        }

    except Exception as erro:
        print(f"\n{nome}: FALHA NA EXTRAÇÃO")
        print(f"Detalhes: {erro}")

        return {
            "nome": nome,
            "status": "FALHA",
            "resultado": None,
            "erro": str(erro)
        }

    finally:
        if bot:
            try:
                bot.fechar()
            except Exception as erro_fechamento:
                print(
                    f"Erro ao fechar o navegador de {nome}: "
                    f"{erro_fechamento}"
                )


def executar():
    print("=" * 60)
    print("PRIME PAINEL - AUTOMAÇÃO SIANNET")
    print("=" * 60)

    robos = [
        ("Escalados", RoboSiannet, "extrair_escalados"),
        ("Performance", RoboPerformance, "extrair_performance"),
        ("Telemetria", RoboTelemetria, "extrair_telemetria"),
        ("Eventos/Viagens", RoboEventosViagens, "extrair_eventos_viagens"),
    ]

    resultados = []

    for nome, classe_robo, metodo_extracao in robos:
        resultados.append(
            executar_robo(nome, classe_robo, metodo_extracao)
        )

    print("\n" + "=" * 60)
    print("RESUMO FINAL - PRIME PAINEL")
    print("=" * 60)

    for item in resultados:
        print(f"{item['nome']}: {item['status']}")
        if item["erro"]:
            print(f"  Motivo: {item['erro']}")

    sucessos = sum(
        1 for item in resultados if item["status"] == "SUCESSO"
    )
    falhas = len(resultados) - sucessos

    print("-" * 60)
    print(f"Robôs concluídos: {sucessos}/{len(resultados)}")
    print(f"Robôs com falha: {falhas}/{len(resultados)}")
    print("=" * 60)


if __name__ == "__main__":
    executar()
