import os
from getpass import getpass

import banco
import config
import regras
from sensor import SensorSimulado
from seed_alunos import sincronizar

PIN_PROFESSOR = config.PIN_PROFESSOR
SENHA_SECRETARIA = config.SENHA_SECRETARIA


def criar_sensor():
    if os.environ.get("SENSOR") == "real":
        from sensor import SensorAS608
        return SensorAS608(os.environ.get("PORTA_SENSOR", "/dev/ttyUSB0"))
    return SensorSimulado()


# ---------------- porta (sensor) ----------------
def modo_porta(sensor):
    print("\n[MODO PORTA] Ctrl+C para voltar ao menu.\n")
    try:
        while True:
            aluno_id = sensor.ler_id()
            if aluno_id is None:
                print("Digital não reconhecida.\n")
                continue
            _, msg = regras.passar_digital(aluno_id)
            print(msg + "\n")
    except KeyboardInterrupt:
        print()


# ---------------- professor ----------------
def painel_professor():
    if getpass("PIN do professor: ") != PIN_PROFESSOR:
        print("PIN incorreto.")
        return

    while True:
        print("\n=== PAINEL DO PROFESSOR ===")
        print("1) Quem está fora agora")
        print("2) Alunos problema")
        print("3) Liberar aluno problema (autoriza 1 saída)")
        print("4) Histórico de um aluno")
        print("0) Voltar")
        op = input("> ").strip()

        if op == "1":
            fora = regras.alunos_fora()
            if not fora:
                print("Ninguém fora da sala.")
            for nome, tempo, atrasado in fora:
                aviso = "  <-- PASSOU DE 3 MIN" if atrasado else ""
                print(f"- {nome}: {regras.fmt(tempo)}{aviso}")

        elif op == "2":
            lista = regras.alunos_problema()
            if not lista:
                print("Nenhum aluno problema.")
            for a in lista:
                status = "liberado p/ 1 saída" if a["liberado"] else "bloqueado"
                print(f"- [{a['id']}] {a['nome']} | estouros: {a['estouros']} | {status}")

        elif op == "3":
            aluno_id = input("ID do aluno: ").strip()
            if aluno_id.isdigit():
                regras.liberar_aluno(int(aluno_id))
                print("Aluno liberado para uma saída.")

        elif op == "4":
            aluno_id = input("ID do aluno: ").strip()
            if aluno_id.isdigit():
                import time
                for s in regras.historico(int(aluno_id)):
                    saida = time.strftime("%d/%m %H:%M:%S", time.localtime(s["saida"]))
                    if s["retorno"] is None:
                        print(f"- {saida} | ainda fora")
                    else:
                        dur = regras.fmt(s["retorno"] - s["saida"])
                        print(f"- {saida} | {dur}{' (ESTOUROU)' if s['estourou'] else ''}")

        elif op == "0":
            return


# ---------------- secretaria ----------------
def painel_secretaria():
    while True:
        print("\n=== PAINEL DA SECRETARIA ===")
        print("1) Alunos problema")
        print("2) Zerar atrasos de um aluno problema")
        print("0) Voltar")
        op = input("> ").strip()

        if op == "1":
            lista = regras.alunos_problema()
            if not lista:
                print("Nenhum aluno problema.")
            for aluno in lista:
                print(f"- [{aluno['id']}] {aluno['nome']} | atrasos: {aluno['estouros']}")

        elif op == "2":
            aluno_id = input("ID do aluno: ").strip()
            if aluno_id.isdigit():
                aluno_id = int(aluno_id)
                if any(aluno["id"] == aluno_id for aluno in regras.alunos_problema()):
                    if getpass("Senha da secretaria: ") == SENHA_SECRETARIA:
                        regras.zerar_contador(aluno_id)
                        print("Atrasos zerados.")
                    else:
                        print("Senha incorreta.")
                else:
                    print("Aluno problema não encontrado.")

        elif op == "0":
            return


def main():
    banco.iniciar()
    sincronizar(silencioso=True)
    sensor = criar_sensor()
    while True:
        print("\n=== CONTROLE DE SAÍDA DA SALA ===")
        print("1) Modo porta (sensor de digital)")
        print("2) Painel do professor")
        print("3) Painel da secretaria")
        print("0) Sair")
        op = input("> ").strip()
        if op == "1":
            modo_porta(sensor)
        elif op == "2":
            painel_professor()
        elif op == "3":
            painel_secretaria()
        elif op == "0":
            break


if __name__ == "__main__":
    main()