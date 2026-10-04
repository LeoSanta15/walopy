# AGENTS.md

Las instrucciones para agentes de IA están en [`CLAUDE.md`](CLAUDE.md): qué es walopy, comandos reales, definición de
«terminado», reglas de trabajo, mapa del código y deuda técnica.

Resumen mínimo:

```bash
make install       # entorno de desarrollo (extras dev, release y docs)
make check-fast    # lint + tipos + tests: iterar con esto
make check         # todo lo que ejecuta el CI: antes de abrir un PR
```

Idioma: español en lo que ve la persona usuaria (mensajes, docstrings, README, commits); identificadores en inglés.
