# DUMP LEDGER — tracked, append-only, written only by `dumps/dump.sh`

**This file is the durable half.** The bytes it points at are gitignored and live only on this
machine; this row survives in git history even after a dump is deleted. So the answer to *"what was
in that dump?"* is never lost, even when the dump is.

**Do not hand-edit.** `dump.sh` assigns the id, stamps UTC, and computes the sha256 — none of them
are typed, because a hand-typed id or digest is a future SYM-039. A row added by hand is a row
nobody can verify.

**Reading a dump is `Historical`, never `Observed`.** It is bytes at a timestamp. It carries no
verdict and proves nothing about now.

| id | utc | lane | category | subject | bytes | sha256 |
|---|---|---|---|---|---|---|
| D0001 | 2026-08-26T05:27:39Z | Fable | evidence | SYM-056 chunk journal snapshot - Ashby, taken before analyst.py rmtree'd it | 3916 | `a9876cfa388f1ef2fe3dbc9b0747d454318d35cdb4932cc58c2e4328334fc9a9` |
| D0002 | 2026-08-27T07:50:55Z | Fable | qa | CHANGELOG backfill S105-S110: 6 drafts + 6 adversarial audits, ALL SIX NEEDS-FIX, deliberately NOT landed | 121147 | `6de8aafbc7627481f8baf27219148ec4a316aa5b0fd85a6d880cea187cc5047b` |
| D0003 | 2026-08-28T02:08:57Z | Fable | qa | FALSIFIED CLASSIFICATION EVIDENCE - 147-row census; st:GOV was invented, NOT DATA | 67491 | `b1efc07dbcab762a75a9dd2e778840f63e9ea65f7eaf40c804ebee5c43bfc123` |
| D0004 | 2026-08-30T16:31:37Z | Fable | evidence | okular fleet full sweep+audit reports (falsified census warning n/a; 404/404 citations audited) | 441225 | `60c3154106a9d7dc9e1158941ea466ee5576ab1a0771a75db0404457c7ba1622` |
| D0005 | 2026-08-30T16:48:17Z | Fable | evidence | okular fleet evidence v2 - sweeps, audits, corrected downgrade metadata (supersedes D0004) | 441639 | `981f295932140acd033668b454760999ad1f5e071f771d9eb793140d8da57099` |
| D0042 | 2026-09-13T00:28:39Z | Fable | evidence | orphaned analyst chunk journal d58db211c41b0e17 (2026-08-30; SURF-12 of the S140 second reading; its book reached DONE 2026-09-01) - ledgered before removal | 2432455 | `75f0304d86f02ec04d7f9bef441074f01ca19e193fd3fa23fc7ca70aaf09f1ce` |
| D0043 | 2026-09-13T11:31:07Z | pipeline | evidence | chunk journal - run 702f1b9661287055 | 701422 | `d9ee8a0b16c640a7d2f398bb769ba097855766af1449c4a39eab91adfc58d776` |
| D0044 | 2026-09-13T17:44:55Z | pipeline | evidence | chunk journal - run da03b7cd2f6403de | 745 | `f4d5dceb6f58d9d9082fde4e4ee0ce89220ddde80972e480979735bb78008afe` |
| D0045 | 2026-09-13T17:44:56Z | pipeline | evidence | chunk journal - run 3717d06965c3f8a7 | 262 | `b2bd6fb09e284c6354a27216816dcadc594ab0d457dc3a95ccdaaa242def29b6` |
| D0046 | 2026-09-13T17:47:18Z | pipeline | evidence | chunk journal - run da03b7cd2f6403de | 745 | `f4d5dceb6f58d9d9082fde4e4ee0ce89220ddde80972e480979735bb78008afe` |
| D0047 | 2026-09-13T17:47:19Z | pipeline | evidence | chunk journal - run 3717d06965c3f8a7 | 262 | `b2bd6fb09e284c6354a27216816dcadc594ab0d457dc3a95ccdaaa242def29b6` |
| D0048 | 2026-09-17T01:35:31Z | pipeline | evidence | chunk journal - run b5c2b2c5ec228c1e | 2128 | `bae42466776887d25d222cedfa8655c59e6f6eb11e5313c44a474b7609be1fee` |
| D0049 | 2026-09-17T01:37:01Z | pipeline | evidence | chunk journal - run c5226dc4e8e096ae | 106 | `1320fd4da654f2d91714e91cc28ff895f41762698ec379ba8a05dd8aee5f1278` |
| D0050 | 2026-09-17T01:58:05Z | pipeline | evidence | chunk journal - run 90d6a69a39aadf0d | 3742 | `7c82246e89f933553e34a739a534f6d88ffab3da72be0b3ead1ba8200e625e1b` |
| D0051 | 2026-09-20T23:05:31Z | pipeline | evidence | chunk journal - run 057a3553750f855d | 929029 | `c0efee3d224ca28932422be271439dd3d0642597fa281ba16e860a133e376c71` |
| D0052 | 2026-09-20T23:31:04Z | pipeline | evidence | chunk journal - run 4eb760efee7e2280 | 322382 | `4e0d5888a152cbe952d5dbdfb154c6a429c17b88ffa2430226360a3c0e9eed7a` |
| D0053 | 2026-09-21T00:46:48Z | pipeline | evidence | chunk journal - run 708b7f0059a3301a | 1549651 | `141adff9212a6d0779d234cbac4f74fcfa3ecb1b3d3649f61eb7a8a4288a9199` |
| D0054 | 2026-09-21T02:03:01Z | pipeline | evidence | ollama server.log tail at a failed call - chunk 384 run f3f3d0ea43e0ebd6 | 19102 | `0319e99db07565412f0f10bd8097fce21ac2a53a9b50f8b597fb1b9ed003589c` |
| D0055 | 2026-09-21T02:07:32Z | pipeline | evidence | chunk journal - run f3f3d0ea43e0ebd6 | 1729633 | `50107ce6f9ebb369724a02b76209708cb3be8b6e8c54c2c6e8b6cecec416d4fb` |
| D0056 | 2026-09-21T02:09:45Z | pipeline | evidence | chunk journal - run bd44a67eb0777cec | 25892 | `f86f9b476bbb767423ee639a51b4680c59a54f42b3dc6e76aa19cf877e0f7f77` |
| D0057 | 2026-09-21T02:18:39Z | pipeline | evidence | ollama server.log tail at a failed call - chunk 21 run 4463b708284154d5 | 19018 | `ad81bbe38fd869034cdd88fd15dbbc18e1ecacf63423549da461b7e1daeac516` |
| D0058 | 2026-09-21T02:25:32Z | pipeline | evidence | ollama server.log tail at a failed call - chunk 55 run 4463b708284154d5 | 18973 | `b269f0a760caf1d713831426f7b17de298f0da9f6c4d4a55012d28df4a1ed622` |
| D0059 | 2026-09-21T02:30:38Z | pipeline | evidence | chunk journal - run 4463b708284154d5 | 356102 | `8a4a91013345f297c3248007fe263a67f4fc766aabdaaee096bb799e6c7dd3cd` |
| D0060 | 2026-09-21T02:52:03Z | pipeline | evidence | chunk journal - run 78a752d1db81916c | 161780 | `bf8ce6f7d0615e9fb7b2eb2401847ec8f3438609a33207c843a36028690df0b9` |
| D0061 | 2026-09-21T03:26:20Z | pipeline | evidence | chunk journal - run f6e0ef3efd733e45 | 382099 | `0007743120c4abdf98b5f25d2c768af8c260ad8a57f9add73f0c53c079f47929` |
| D0062 | 2026-09-21T03:30:52Z | pipeline | evidence | chunk journal - run 288d10869855e1c4 | 40864 | `eae2b30cfb853150bf9f15c304684836f083e51562f6fc844e6b2dde3484c9ae` |
| D0063 | 2026-09-21T04:17:11Z | pipeline | evidence | chunk journal - run 145b3f71759d3794 | 582618 | `ccfa0e6fe4ca4afd00bd0c36adb7122c0db421ba09609dbaadc81566e00504b5` |
| D0064 | 2026-09-21T05:22:01Z | pipeline | evidence | chunk journal - run bff17643c228f5de | 1020713 | `a508d7cd412681cf6a48d001f0a33bb684df3accd4fea804bd5ee5ac863cff18` |
| D0065 | 2026-09-21T06:02:07Z | pipeline | evidence | chunk journal - run 4a938ca1d027a746 | 662444 | `8065c49be5a957ca01edc807eafa2b2fa758c2bed8300e48032e6c43a16814a8` |
| D0066 | 2026-09-21T09:14:01Z | pipeline | evidence | chunk journal - run 18634006fde43375 | 2323789 | `31fc28bc27ae4713aa1a5dcf99d34571ad52fa56242b22de894042e8aadd8fb4` |
| D0067 | 2026-09-21T11:15:22Z | pipeline | evidence | chunk journal - run 996ee2e7e01f4744 | 1375043 | `9c87528091882ab83b9396ba01591cb2f2bdbc1682d0f015828bea053417c57a` |
| D0068 | 2026-09-21T12:50:28Z | pipeline | evidence | chunk journal - run 264593315026926a | 1685643 | `8973957369b41cc6a4700ba7f2a94b57201f5bf9b39a8df638f7ee3bf5a0c752` |
| D0069 | 2026-09-21T13:18:46Z | pipeline | evidence | chunk journal - run 507041b00b9602fe | 337062 | `b0f9848a5cacfe206a28c04496f0e86f2a0b97a7dcfded0c2ed9faec02ec4d0d` |
| D0070 | 2026-09-21T13:50:13Z | pipeline | evidence | chunk journal - run d3f86e2d43c9c5c6 | 361345 | `29cbd40457453ecccd1f47685f03bb876aba7bdcb911e1dff8eb1953de06005d` |
| D0071 | 2026-09-21T13:56:05Z | pipeline | evidence | chunk journal - run 7f2f359448470dad | 80896 | `3c9ceaffc1973994067185c5dc923bf987fe49e06c78971220ce4e72b1644d47` |
| D0072 | 2026-09-21T14:15:09Z | pipeline | evidence | chunk journal - run 058c279d41f6cc7c | 149489 | `7a2ca6298173052bd3192fae19e04d3c0a9f68bf080cf270d683aaf9dfd29d8a` |
| D0073 | 2026-09-21T14:16:56Z | pipeline | evidence | chunk journal - run 0c2916f6f3f6a94b | 9589 | `0a811460d14e3e2890d58c17b8d61587ec0301d0c79b500e022c922eedb966ad` |
| D0074 | 2026-09-21T19:49:43Z | pipeline | evidence | chunk journal - run 0c2916f6f3f6a94b | 9589 | `0a811460d14e3e2890d58c17b8d61587ec0301d0c79b500e022c922eedb966ad` |
| D0075 | 2026-09-21T19:51:25Z | pipeline | evidence | chunk journal - run 308e10ba7636344f | 9625 | `c998eb53a6f7946918da2dfe8e9c6688ab4b714582145dd138e68ed11dc5b8d1` |
| D0076 | 2026-09-21T20:26:40Z | pipeline | evidence | chunk journal - run 058c279d41f6cc7c | 149489 | `7a2ca6298173052bd3192fae19e04d3c0a9f68bf080cf270d683aaf9dfd29d8a` |
| D0077 | 2026-09-21T23:01:44Z | pipeline | evidence | chunk journal - run 76247681dd600a70 | 1972815 | `cdc9fa2bb0ca528cc9dcc3addfd93ec56cdcf31cb9bdb21711c98a6612a9a5bd` |
| D0078 | 2026-09-21T23:23:52Z | pipeline | evidence | chunk journal - run 64a148741140dfa7 | 149223 | `2ee8d0bca260cb1fa58a738bb6ab28d6792b6f523c84be9f1964b7fa2d835a0d` |
| D0079 | 2026-09-22T01:27:10Z | pipeline | evidence | chunk journal - run b6210d0e9cd29cfa | 1578135 | `0c3a2e5d6ef61834a5cf76a8a07b90dd84f72bd50d1af69fa7ed72a06b38d794` |
| D0080 | 2026-09-22T01:58:17Z | pipeline | evidence | chunk journal - run 6edf23beccf343e6 | 337176 | `6df937b667aab81aaa2777fb7be100c0b0c36bca6169f283efdb679fb03704de` |
| D0081 | 2026-09-22T02:41:57Z | pipeline | evidence | chunk journal - run 6a65292199282359 | 655861 | `175432a212550b04456e3405f7dd5b6bccb938b31b2c3a19a44a9158d082dbea` |
| D0082 | 2026-09-22T04:18:47Z | pipeline | evidence | chunk journal - run 2c571faaad59651a | 1370792 | `ede59e55cde3cb14256acdaf7181dc807830e0aa02067202752d23dfa93fd416` |
| D0083 | 2026-09-22T06:12:09Z | pipeline | evidence | chunk journal - run d1f9439f6f00e4a5 | 1596924 | `c1eedd390c8b4d533a346b66bfcb6bafb3483a423dcf25c611c06248a8bc5301` |
