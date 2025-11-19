#!/usr/bin/env python3
"""
Script de teste para validar a robustez da solução de gerenciamento de drivers.
Testa múltiplas requisições simultâneas e sequenciais para verificar se há vazamento.
"""

import asyncio
import aiohttp
import time
import sys
import json
from datetime import datetime, timedelta
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configurações
BASE_URL = "http://localhost:8001"
API_KEY = "test123"  # Ajuste conforme necessário

class RobustnessTest:
    """Classe para testar robustez do sistema"""

    def __init__(self, base_url=BASE_URL):
        self.base_url = base_url
        self.stats = {
            "total_requests": 0,
            "successful": 0,
            "failed": 0,
            "errors": []
        }

    async def check_driver_stats(self, session):
        """Verifica estatísticas de drivers"""
        try:
            async with session.get(f"{self.base_url}/api/driver-stats") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    active = data.get('drivers', {}).get('active_count', 0)
                    logger.info(f"📊 Drivers ativos: {active}")
                    return active
                else:
                    logger.warning(f"⚠️ Erro ao obter stats: {resp.status}")
                    return -1
        except Exception as e:
            logger.error(f"❌ Erro ao verificar drivers: {e}")
            return -1

    async def check_health(self, session):
        """Verifica health do sistema"""
        try:
            async with session.get(f"{self.base_url}/health") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    status = data.get('status', 'unknown')
                    memory = data.get('memory', {}).get('used_percent', -1)
                    logger.info(f"🏥 Health: {status} | Memória: {memory:.1f}%")
                    return status, memory
                else:
                    return "error", -1
        except Exception as e:
            logger.error(f"❌ Erro no health check: {e}")
            return "error", -1

    async def process_ecomhub_request(self, session, request_id, date_range):
        """Faz uma requisição ao endpoint principal"""
        start_time = time.time()

        payload = {
            "data_inicio": date_range[0],
            "data_fim": date_range[1],
            "pais_id": "164"  # Espanha
        }

        try:
            logger.info(f"🚀 Requisição #{request_id} iniciada")

            async with session.post(
                f"{self.base_url}/api/processar-ecomhub/",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=60)
            ) as resp:
                elapsed = time.time() - start_time

                if resp.status == 200:
                    data = await resp.json()
                    total_records = data.get('estatisticas', {}).get('total_registros', 0)
                    logger.info(f"✅ Requisição #{request_id} OK - {total_records} registros em {elapsed:.1f}s")
                    self.stats["successful"] += 1
                    return True
                else:
                    text = await resp.text()
                    logger.error(f"❌ Requisição #{request_id} falhou: {resp.status} - {text[:100]}")
                    self.stats["failed"] += 1
                    self.stats["errors"].append({
                        "request_id": request_id,
                        "status": resp.status,
                        "error": text[:200]
                    })
                    return False

        except asyncio.TimeoutError:
            elapsed = time.time() - start_time
            logger.error(f"⏱️ Requisição #{request_id} timeout após {elapsed:.1f}s")
            self.stats["failed"] += 1
            self.stats["errors"].append({
                "request_id": request_id,
                "error": "Timeout"
            })
            return False

        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"❌ Requisição #{request_id} erro: {e} após {elapsed:.1f}s")
            self.stats["failed"] += 1
            self.stats["errors"].append({
                "request_id": request_id,
                "error": str(e)
            })
            return False

        finally:
            self.stats["total_requests"] += 1

    async def test_sequential(self, num_requests=10):
        """Testa requisições sequenciais"""
        logger.info(f"\n🔄 Teste Sequencial - {num_requests} requisições")
        logger.info("=" * 50)

        async with aiohttp.ClientSession() as session:
            # Check inicial
            await self.check_health(session)
            initial_drivers = await self.check_driver_stats(session)

            # Executar requisições sequencialmente
            for i in range(1, num_requests + 1):
                # Variar datas para evitar cache
                days_back = i % 30
                date_start = (datetime.now() - timedelta(days=30 + days_back)).strftime("%Y-%m-%d")
                date_end = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")

                await self.process_ecomhub_request(session, i, (date_start, date_end))

                # Verificar drivers a cada 3 requisições
                if i % 3 == 0:
                    await self.check_driver_stats(session)

                # Pequena pausa entre requisições
                await asyncio.sleep(1)

            # Check final
            await asyncio.sleep(2)
            final_drivers = await self.check_driver_stats(session)
            health_status, memory = await self.check_health(session)

            logger.info("\n📈 Resultado Teste Sequencial:")
            logger.info(f"  Total: {self.stats['total_requests']}")
            logger.info(f"  ✅ Sucesso: {self.stats['successful']}")
            logger.info(f"  ❌ Falhas: {self.stats['failed']}")
            logger.info(f"  🚗 Drivers inicial→final: {initial_drivers}→{final_drivers}")
            logger.info(f"  💾 Memória final: {memory:.1f}%")
            logger.info(f"  🏥 Health final: {health_status}")

            return self.stats["failed"] == 0

    async def test_concurrent(self, num_concurrent=3, num_batches=3):
        """Testa requisições concorrentes"""
        logger.info(f"\n⚡ Teste Concorrente - {num_concurrent} simultâneas x {num_batches} batches")
        logger.info("=" * 50)

        async with aiohttp.ClientSession() as session:
            # Check inicial
            await self.check_health(session)
            initial_drivers = await self.check_driver_stats(session)

            request_id = 0
            for batch in range(1, num_batches + 1):
                logger.info(f"\n🎯 Batch {batch}/{num_batches}")

                # Criar tarefas concorrentes
                tasks = []
                for i in range(num_concurrent):
                    request_id += 1
                    days_back = request_id % 30
                    date_start = (datetime.now() - timedelta(days=30 + days_back)).strftime("%Y-%m-%d")
                    date_end = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")

                    task = self.process_ecomhub_request(session, request_id, (date_start, date_end))
                    tasks.append(task)

                # Executar batch concorrentemente
                results = await asyncio.gather(*tasks, return_exceptions=True)

                # Verificar drivers após cada batch
                await self.check_driver_stats(session)

                # Pausa entre batches
                await asyncio.sleep(2)

            # Check final
            await asyncio.sleep(3)
            final_drivers = await self.check_driver_stats(session)
            health_status, memory = await self.check_health(session)

            logger.info("\n📈 Resultado Teste Concorrente:")
            logger.info(f"  Total: {self.stats['total_requests']}")
            logger.info(f"  ✅ Sucesso: {self.stats['successful']}")
            logger.info(f"  ❌ Falhas: {self.stats['failed']}")
            logger.info(f"  🚗 Drivers inicial→final: {initial_drivers}→{final_drivers}")
            logger.info(f"  💾 Memória final: {memory:.1f}%")
            logger.info(f"  🏥 Health final: {health_status}")

            return self.stats["failed"] == 0

    async def test_stress(self, duration_seconds=60):
        """Teste de stress contínuo"""
        logger.info(f"\n🔥 Teste de Stress - {duration_seconds} segundos")
        logger.info("=" * 50)

        async with aiohttp.ClientSession() as session:
            start_time = time.time()
            request_id = 0

            # Check inicial
            await self.check_health(session)
            initial_drivers = await self.check_driver_stats(session)

            while (time.time() - start_time) < duration_seconds:
                request_id += 1

                # Variar datas
                days_back = request_id % 30
                date_start = (datetime.now() - timedelta(days=30 + days_back)).strftime("%Y-%m-%d")
                date_end = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")

                # Fazer requisição
                asyncio.create_task(
                    self.process_ecomhub_request(session, request_id, (date_start, date_end))
                )

                # Verificar periodicamente
                if request_id % 5 == 0:
                    await self.check_driver_stats(session)
                    health_status, memory = await self.check_health(session)

                    if health_status == "critical" or memory > 90:
                        logger.warning("⚠️ Sistema em estado crítico, pausando teste...")
                        break

                # Controlar taxa de requisições
                await asyncio.sleep(2)  # Uma requisição a cada 2 segundos

            # Aguardar tarefas pendentes
            await asyncio.sleep(5)

            # Check final
            final_drivers = await self.check_driver_stats(session)
            health_status, memory = await self.check_health(session)

            elapsed = time.time() - start_time
            req_per_sec = self.stats['total_requests'] / elapsed if elapsed > 0 else 0

            logger.info("\n📈 Resultado Teste de Stress:")
            logger.info(f"  Duração: {elapsed:.1f} segundos")
            logger.info(f"  Total: {self.stats['total_requests']}")
            logger.info(f"  Taxa: {req_per_sec:.2f} req/s")
            logger.info(f"  ✅ Sucesso: {self.stats['successful']}")
            logger.info(f"  ❌ Falhas: {self.stats['failed']}")
            logger.info(f"  Taxa sucesso: {(self.stats['successful']/max(1,self.stats['total_requests'])*100):.1f}%")
            logger.info(f"  🚗 Drivers inicial→final: {initial_drivers}→{final_drivers}")
            logger.info(f"  💾 Memória final: {memory:.1f}%")
            logger.info(f"  🏥 Health final: {health_status}")

            return self.stats["failed"] < self.stats["successful"]

    async def cleanup_drivers(self, session):
        """Força limpeza de drivers"""
        logger.info("🧹 Forçando limpeza de drivers...")
        try:
            headers = {"X-API-Key": API_KEY}
            async with session.post(
                f"{self.base_url}/api/cleanup",
                headers=headers
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    logger.info(f"✅ Limpeza executada: {data}")
                else:
                    logger.warning(f"⚠️ Erro na limpeza: {resp.status}")
        except Exception as e:
            logger.error(f"❌ Erro ao limpar: {e}")


async def main():
    """Função principal"""
    logger.info("🚀 Iniciando testes de robustez")
    logger.info(f"📍 URL Base: {BASE_URL}")
    logger.info("=" * 60)

    # Verificar se servidor está rodando
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{BASE_URL}/health", timeout=aiohttp.ClientTimeout(total=5)) as resp:
                if resp.status != 200:
                    logger.error("❌ Servidor não está respondendo!")
                    return
    except Exception as e:
        logger.error(f"❌ Erro ao conectar ao servidor: {e}")
        logger.error("Certifique-se que o servidor está rodando em http://localhost:8001")
        return

    # Executar testes
    test = RobustnessTest(BASE_URL)

    # Reset stats para cada teste
    test.stats = {"total_requests": 0, "successful": 0, "failed": 0, "errors": []}

    # 1. Teste Sequencial
    success = await test.test_sequential(num_requests=10)
    if not success:
        logger.warning("⚠️ Teste sequencial falhou")

    # Limpar entre testes
    async with aiohttp.ClientSession() as session:
        await test.cleanup_drivers(session)
    await asyncio.sleep(3)

    # Reset stats
    test.stats = {"total_requests": 0, "successful": 0, "failed": 0, "errors": []}

    # 2. Teste Concorrente
    success = await test.test_concurrent(num_concurrent=3, num_batches=3)
    if not success:
        logger.warning("⚠️ Teste concorrente falhou")

    # Limpar entre testes
    async with aiohttp.ClientSession() as session:
        await test.cleanup_drivers(session)
    await asyncio.sleep(3)

    # Reset stats
    test.stats = {"total_requests": 0, "successful": 0, "failed": 0, "errors": []}

    # 3. Teste de Stress (opcional - descomente para executar)
    # success = await test.test_stress(duration_seconds=60)
    # if not success:
    #     logger.warning("⚠️ Teste de stress falhou")

    # Resultado final
    logger.info("\n" + "=" * 60)
    logger.info("🏁 TESTES CONCLUÍDOS")

    if test.stats["errors"]:
        logger.info("\n❌ Erros encontrados:")
        for error in test.stats["errors"][:5]:  # Mostrar até 5 erros
            logger.info(f"  - {error}")

    # Verificação final
    async with aiohttp.ClientSession() as session:
        drivers = await test.check_driver_stats(session)
        health, memory = await test.check_health(session)

        if drivers == 0 and health != "critical":
            logger.info("\n✅ SUCESSO: Sistema está robusto!")
            logger.info("  - Sem vazamento de drivers")
            logger.info("  - Memória estável")
            logger.info("  - Pronto para produção")
        else:
            logger.warning("\n⚠️ ATENÇÃO: Verificar sistema")
            logger.warning(f"  - Drivers ativos: {drivers}")
            logger.warning(f"  - Health: {health}")
            logger.warning(f"  - Memória: {memory:.1f}%")


if __name__ == "__main__":
    # Rodar testes
    asyncio.run(main())