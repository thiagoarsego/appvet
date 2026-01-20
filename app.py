import sqlite3
import tkinter as tk
from datetime import datetime, date
from tkinter import messagebox, ttk


DB_PATH = "banho_tosa.db"
STATUS_FLOW = ["Aguardando", "Em banho", "Em tosa", "Pronto", "Entregue"]


class Database:
    def __init__(self, path=DB_PATH):
        self.path = path
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self.create_tables()

    def create_tables(self):
        cursor = self.conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS clientes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                telefone TEXT NOT NULL
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS pets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cliente_id INTEGER NOT NULL,
                nome TEXT NOT NULL,
                especie TEXT NOT NULL,
                raca TEXT NOT NULL,
                porte TEXT NOT NULL,
                observacoes TEXT,
                FOREIGN KEY (cliente_id) REFERENCES clientes(id)
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS atendimentos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cliente_id INTEGER NOT NULL,
                pet_id INTEGER NOT NULL,
                servico TEXT NOT NULL,
                status TEXT NOT NULL,
                hora_entrada TEXT NOT NULL,
                hora_saida TEXT,
                valor REAL NOT NULL,
                data_atendimento TEXT NOT NULL,
                FOREIGN KEY (cliente_id) REFERENCES clientes(id),
                FOREIGN KEY (pet_id) REFERENCES pets(id)
            )
            """
        )
        self.conn.commit()

    def add_cliente(self, nome, telefone):
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO clientes (nome, telefone) VALUES (?, ?)",
            (nome, telefone),
        )
        self.conn.commit()

    def list_clientes(self):
        cursor = self.conn.cursor()
        return cursor.execute("SELECT * FROM clientes ORDER BY nome").fetchall()

    def add_pet(self, cliente_id, nome, especie, raca, porte, observacoes):
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO pets (cliente_id, nome, especie, raca, porte, observacoes)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (cliente_id, nome, especie, raca, porte, observacoes),
        )
        self.conn.commit()

    def list_pets(self, cliente_id=None):
        cursor = self.conn.cursor()
        if cliente_id:
            return cursor.execute(
                "SELECT * FROM pets WHERE cliente_id = ? ORDER BY nome",
                (cliente_id,),
            ).fetchall()
        return cursor.execute("SELECT * FROM pets ORDER BY nome").fetchall()

    def add_atendimento(self, cliente_id, pet_id, servico, status, hora_entrada, valor):
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO atendimentos
                (cliente_id, pet_id, servico, status, hora_entrada, hora_saida, valor, data_atendimento)
            VALUES (?, ?, ?, ?, ?, NULL, ?, ?)
            """,
            (
                cliente_id,
                pet_id,
                servico,
                status,
                hora_entrada,
                valor,
                date.today().isoformat(),
            ),
        )
        self.conn.commit()

    def update_atendimento(self, atendimento_id, servico, status, valor):
        cursor = self.conn.cursor()
        cursor.execute(
            """
            UPDATE atendimentos
            SET servico = ?, status = ?, valor = ?
            WHERE id = ?
            """,
            (servico, status, valor, atendimento_id),
        )
        self.conn.commit()

    def update_status(self, atendimento_id, status):
        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE atendimentos SET status = ? WHERE id = ?",
            (status, atendimento_id),
        )
        self.conn.commit()

    def finalizar_atendimento(self, atendimento_id, hora_saida, status):
        cursor = self.conn.cursor()
        cursor.execute(
            """
            UPDATE atendimentos
            SET hora_saida = ?, status = ?
            WHERE id = ?
            """,
            (hora_saida, status, atendimento_id),
        )
        self.conn.commit()

    def list_atendimentos(self, filtro=None):
        cursor = self.conn.cursor()
        query = (
            """
            SELECT atendimentos.*, clientes.nome AS cliente_nome, pets.nome AS pet_nome
            FROM atendimentos
            JOIN clientes ON clientes.id = atendimentos.cliente_id
            JOIN pets ON pets.id = atendimentos.pet_id
            WHERE atendimentos.data_atendimento = ?
            """
        )
        params = [date.today().isoformat()]
        if filtro:
            query += " AND (clientes.nome LIKE ? OR pets.nome LIKE ?)"
            term = f"%{filtro}%"
            params.extend([term, term])
        query += " ORDER BY atendimentos.hora_entrada DESC"
        return cursor.execute(query, params).fetchall()

    def resumo_dia(self):
        cursor = self.conn.cursor()
        row = cursor.execute(
            """
            SELECT COUNT(*) AS total, COALESCE(SUM(valor), 0) AS soma
            FROM atendimentos
            WHERE data_atendimento = ?
            """,
            (date.today().isoformat(),),
        ).fetchone()
        return row["total"], row["soma"]


class AtendimentoForm(tk.Toplevel):
    def __init__(self, master, db, on_save, atendimento=None):
        super().__init__(master)
        self.db = db
        self.on_save = on_save
        self.atendimento = atendimento
        self.title("Atendimento")
        self.resizable(False, False)

        self.cliente_var = tk.StringVar()
        self.pet_var = tk.StringVar()
        self.servico_var = tk.StringVar()
        self.status_var = tk.StringVar(value=STATUS_FLOW[0])
        self.valor_var = tk.StringVar()

        self.clientes = self.db.list_clientes()
        self.pets = []

        self.build()
        self.load_initial_data()

    def build(self):
        padding = {"padx": 10, "pady": 5}
        ttk.Label(self, text="Cliente").grid(row=0, column=0, sticky="w", **padding)
        self.cliente_cb = ttk.Combobox(
            self, textvariable=self.cliente_var, state="readonly", width=30
        )
        self.cliente_cb.grid(row=0, column=1, **padding)
        self.cliente_cb.bind("<<ComboboxSelected>>", self.on_cliente_change)

        ttk.Label(self, text="Pet").grid(row=1, column=0, sticky="w", **padding)
        self.pet_cb = ttk.Combobox(
            self, textvariable=self.pet_var, state="readonly", width=30
        )
        self.pet_cb.grid(row=1, column=1, **padding)

        ttk.Label(self, text="Serviço").grid(row=2, column=0, sticky="w", **padding)
        ttk.Entry(self, textvariable=self.servico_var, width=33).grid(
            row=2, column=1, **padding
        )

        ttk.Label(self, text="Status").grid(row=3, column=0, sticky="w", **padding)
        self.status_cb = ttk.Combobox(
            self,
            textvariable=self.status_var,
            values=STATUS_FLOW,
            state="readonly",
            width=30,
        )
        self.status_cb.grid(row=3, column=1, **padding)

        ttk.Label(self, text="Valor (R$)").grid(row=4, column=0, sticky="w", **padding)
        ttk.Entry(self, textvariable=self.valor_var, width=33).grid(
            row=4, column=1, **padding
        )

        button_frame = ttk.Frame(self)
        button_frame.grid(row=5, column=0, columnspan=2, pady=10)
        ttk.Button(button_frame, text="Salvar", command=self.save).pack(
            side="left", padx=5
        )
        ttk.Button(button_frame, text="Cancelar", command=self.destroy).pack(
            side="left", padx=5
        )

    def load_initial_data(self):
        self.cliente_cb["values"] = [c["nome"] for c in self.clientes]
        if self.clientes:
            self.cliente_cb.current(0)
            self.on_cliente_change()

        if self.atendimento:
            cliente_nome = self.atendimento["cliente_nome"]
            pet_nome = self.atendimento["pet_nome"]
            self.cliente_var.set(cliente_nome)
            self.on_cliente_change()
            self.pet_var.set(pet_nome)
            self.servico_var.set(self.atendimento["servico"])
            self.status_var.set(self.atendimento["status"])
            self.valor_var.set(f"{self.atendimento['valor']:.2f}")

    def on_cliente_change(self, *_):
        cliente_id = self.get_cliente_id()
        self.pets = self.db.list_pets(cliente_id)
        self.pet_cb["values"] = [p["nome"] for p in self.pets]
        if self.pets:
            self.pet_cb.current(0)
        else:
            self.pet_var.set("")

    def get_cliente_id(self):
        name = self.cliente_var.get()
        for cliente in self.clientes:
            if cliente["nome"] == name:
                return cliente["id"]
        return None

    def get_pet_id(self):
        name = self.pet_var.get()
        for pet in self.pets:
            if pet["nome"] == name:
                return pet["id"]
        return None

    def save(self):
        cliente_id = self.get_cliente_id()
        pet_id = self.get_pet_id()
        servico = self.servico_var.get().strip()
        status = self.status_var.get()
        valor_text = self.valor_var.get().replace(",", ".").strip()

        if not cliente_id or not pet_id:
            messagebox.showwarning("Dados inválidos", "Selecione cliente e pet.")
            return
        if not servico:
            messagebox.showwarning("Dados inválidos", "Informe o serviço.")
            return
        try:
            valor = float(valor_text)
        except ValueError:
            messagebox.showwarning("Dados inválidos", "Informe um valor válido.")
            return

        if self.atendimento:
            self.db.update_atendimento(self.atendimento["id"], servico, status, valor)
        else:
            hora_entrada = datetime.now().strftime("%H:%M")
            self.db.add_atendimento(cliente_id, pet_id, servico, status, hora_entrada, valor)

        self.on_save()
        self.destroy()


class ClienteForm(tk.Toplevel):
    def __init__(self, master, db, on_save):
        super().__init__(master)
        self.db = db
        self.on_save = on_save
        self.title("Cadastrar cliente")
        self.resizable(False, False)

        self.nome_var = tk.StringVar()
        self.telefone_var = tk.StringVar()

        padding = {"padx": 10, "pady": 5}
        ttk.Label(self, text="Nome").grid(row=0, column=0, sticky="w", **padding)
        ttk.Entry(self, textvariable=self.nome_var, width=35).grid(
            row=0, column=1, **padding
        )

        ttk.Label(self, text="Telefone").grid(row=1, column=0, sticky="w", **padding)
        ttk.Entry(self, textvariable=self.telefone_var, width=35).grid(
            row=1, column=1, **padding
        )

        button_frame = ttk.Frame(self)
        button_frame.grid(row=2, column=0, columnspan=2, pady=10)
        ttk.Button(button_frame, text="Salvar", command=self.save).pack(
            side="left", padx=5
        )
        ttk.Button(button_frame, text="Cancelar", command=self.destroy).pack(
            side="left", padx=5
        )

    def save(self):
        nome = self.nome_var.get().strip()
        telefone = self.telefone_var.get().strip()
        if not nome or not telefone:
            messagebox.showwarning("Dados inválidos", "Informe nome e telefone.")
            return
        self.db.add_cliente(nome, telefone)
        self.on_save()
        self.destroy()


class PetForm(tk.Toplevel):
    def __init__(self, master, db, on_save):
        super().__init__(master)
        self.db = db
        self.on_save = on_save
        self.title("Cadastrar pet")
        self.resizable(False, False)

        self.cliente_var = tk.StringVar()
        self.nome_var = tk.StringVar()
        self.especie_var = tk.StringVar()
        self.raca_var = tk.StringVar()
        self.porte_var = tk.StringVar()
        self.obs_var = tk.StringVar()

        self.clientes = self.db.list_clientes()

        padding = {"padx": 10, "pady": 5}
        ttk.Label(self, text="Cliente").grid(row=0, column=0, sticky="w", **padding)
        self.cliente_cb = ttk.Combobox(
            self, textvariable=self.cliente_var, state="readonly", width=30
        )
        self.cliente_cb.grid(row=0, column=1, **padding)
        self.cliente_cb["values"] = [c["nome"] for c in self.clientes]
        if self.clientes:
            self.cliente_cb.current(0)

        ttk.Label(self, text="Nome").grid(row=1, column=0, sticky="w", **padding)
        ttk.Entry(self, textvariable=self.nome_var, width=33).grid(
            row=1, column=1, **padding
        )

        ttk.Label(self, text="Espécie").grid(row=2, column=0, sticky="w", **padding)
        ttk.Entry(self, textvariable=self.especie_var, width=33).grid(
            row=2, column=1, **padding
        )

        ttk.Label(self, text="Raça").grid(row=3, column=0, sticky="w", **padding)
        ttk.Entry(self, textvariable=self.raca_var, width=33).grid(
            row=3, column=1, **padding
        )

        ttk.Label(self, text="Porte").grid(row=4, column=0, sticky="w", **padding)
        ttk.Entry(self, textvariable=self.porte_var, width=33).grid(
            row=4, column=1, **padding
        )

        ttk.Label(self, text="Observações").grid(
            row=5, column=0, sticky="w", **padding
        )
        ttk.Entry(self, textvariable=self.obs_var, width=33).grid(
            row=5, column=1, **padding
        )

        button_frame = ttk.Frame(self)
        button_frame.grid(row=6, column=0, columnspan=2, pady=10)
        ttk.Button(button_frame, text="Salvar", command=self.save).pack(
            side="left", padx=5
        )
        ttk.Button(button_frame, text="Cancelar", command=self.destroy).pack(
            side="left", padx=5
        )

    def save(self):
        cliente_nome = self.cliente_var.get()
        cliente_id = None
        for cliente in self.clientes:
            if cliente["nome"] == cliente_nome:
                cliente_id = cliente["id"]
                break
        if not cliente_id:
            messagebox.showwarning("Dados inválidos", "Selecione um cliente.")
            return
        nome = self.nome_var.get().strip()
        especie = self.especie_var.get().strip()
        raca = self.raca_var.get().strip()
        porte = self.porte_var.get().strip()
        observacoes = self.obs_var.get().strip()
        if not all([nome, especie, raca, porte]):
            messagebox.showwarning("Dados inválidos", "Preencha todos os campos.")
            return
        self.db.add_pet(cliente_id, nome, especie, raca, porte, observacoes)
        self.on_save()
        self.destroy()


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.db = Database()
        self.title("Controle de Banho e Tosa")
        self.geometry("980x600")
        self.search_var = tk.StringVar()
        self.total_var = tk.StringVar()
        self.soma_var = tk.StringVar()
        self.build()
        self.refresh_atendimentos()

    def build(self):
        header = ttk.Frame(self)
        header.pack(fill="x", padx=10, pady=10)
        ttk.Label(
            header,
            text="Fila do dia",
            font=("Segoe UI", 16, "bold"),
        ).pack(side="left")

        resumo = ttk.Frame(header)
        resumo.pack(side="right")
        ttk.Label(resumo, text="Total atendimentos:").grid(row=0, column=0, sticky="e")
        ttk.Label(resumo, textvariable=self.total_var, width=5).grid(
            row=0, column=1, padx=5
        )
        ttk.Label(resumo, text="Soma (R$):").grid(row=0, column=2, sticky="e")
        ttk.Label(resumo, textvariable=self.soma_var, width=10).grid(
            row=0, column=3, padx=5
        )

        controls = ttk.Frame(self)
        controls.pack(fill="x", padx=10)

        ttk.Label(controls, text="Buscar (tutor ou pet):").pack(side="left")
        search_entry = ttk.Entry(controls, textvariable=self.search_var, width=30)
        search_entry.pack(side="left", padx=5)
        search_entry.bind("<KeyRelease>", lambda *_: self.refresh_atendimentos())

        ttk.Button(controls, text="Cadastrar cliente", command=self.open_cliente).pack(
            side="right", padx=5
        )
        ttk.Button(controls, text="Cadastrar pet", command=self.open_pet).pack(
            side="right", padx=5
        )

        columns = (
            "tutor",
            "pet",
            "servico",
            "status",
            "entrada",
            "saida",
            "valor",
        )
        self.tree = ttk.Treeview(self, columns=columns, show="headings", height=18)
        self.tree.pack(fill="both", expand=True, padx=10, pady=10)
        headings = {
            "tutor": "Tutor",
            "pet": "Pet",
            "servico": "Serviço",
            "status": "Status",
            "entrada": "Hora entrada",
            "saida": "Hora saída",
            "valor": "Valor",
        }
        for col in columns:
            self.tree.heading(col, text=headings[col])
            self.tree.column(col, width=120, anchor="center")

        actions = ttk.Frame(self)
        actions.pack(fill="x", padx=10, pady=5)
        ttk.Button(actions, text="Novo atendimento", command=self.open_atendimento).pack(
            side="left", padx=5
        )
        ttk.Button(actions, text="Editar", command=self.edit_atendimento).pack(
            side="left", padx=5
        )
        ttk.Button(
            actions, text="Mudar status", command=self.change_status
        ).pack(side="left", padx=5)
        ttk.Button(actions, text="Finalizar", command=self.finalizar).pack(
            side="left", padx=5
        )

    def refresh_atendimentos(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        filtro = self.search_var.get().strip()
        atendimentos = self.db.list_atendimentos(filtro=filtro)
        for atendimento in atendimentos:
            self.tree.insert(
                "",
                "end",
                iid=str(atendimento["id"]),
                values=(
                    atendimento["cliente_nome"],
                    atendimento["pet_nome"],
                    atendimento["servico"],
                    atendimento["status"],
                    atendimento["hora_entrada"],
                    atendimento["hora_saida"] or "-",
                    f"R$ {atendimento['valor']:.2f}",
                ),
            )
        total, soma = self.db.resumo_dia()
        self.total_var.set(str(total))
        self.soma_var.set(f"{soma:.2f}")

    def open_atendimento(self):
        if not self.db.list_clientes():
            messagebox.showwarning(
                "Cadastro necessário", "Cadastre um cliente antes do atendimento."
            )
            return
        AtendimentoForm(self, self.db, self.refresh_atendimentos)

    def get_selected(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Seleção", "Selecione um atendimento.")
            return None
        atendimento_id = int(selected[0])
        return next(
            (a for a in self.db.list_atendimentos() if a["id"] == atendimento_id),
            None,
        )

    def edit_atendimento(self):
        atendimento = self.get_selected()
        if atendimento:
            AtendimentoForm(self, self.db, self.refresh_atendimentos, atendimento)

    def change_status(self):
        atendimento = self.get_selected()
        if atendimento:
            status = atendimento["status"]
            try:
                idx = STATUS_FLOW.index(status)
            except ValueError:
                idx = 0
            new_status = STATUS_FLOW[(idx + 1) % len(STATUS_FLOW)]
            self.db.update_status(atendimento["id"], new_status)
            self.refresh_atendimentos()

    def finalizar(self):
        atendimento = self.get_selected()
        if atendimento:
            hora_saida = datetime.now().strftime("%H:%M")
            self.db.finalizar_atendimento(atendimento["id"], hora_saida, "Entregue")
            self.refresh_atendimentos()

    def open_cliente(self):
        ClienteForm(self, self.db, self.refresh_atendimentos)

    def open_pet(self):
        if not self.db.list_clientes():
            messagebox.showwarning(
                "Cadastro necessário", "Cadastre um cliente antes do pet."
            )
            return
        PetForm(self, self.db, self.refresh_atendimentos)


if __name__ == "__main__":
    app = App()
    app.mainloop()
