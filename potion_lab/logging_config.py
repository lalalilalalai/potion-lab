"""Конфигурация logging в точке запуска процесса."""

import logging

LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s %(message)s"
STARTUP_ART = r"""
⋆｡🜁♄°✩ Salem! вич хаус кор аэстетикс апп инициализировано ✩°｡⋆☽☉☿
               (       "     )
                ( _  *
                   * (     /      \    ___
                      "     "        _/ /
                     (   *  )    ___/   |
                       )   "     _ o)'-./__
                      *  _ )    (_, . $$$
                      (  )   __ __ 7_ $$$$
                       ( :  { _)  '---  $\
                  ______'___//__\   ____, \
                   )           ( \_/ _____\_
                 .'             \   \------''.
                 |='           '=|  |         )
                 |               |  |  .    _/
                  \    (. ) ,   /  /__I_____\
              snd  '._/_)_(\__.'   (__,(__,_]
                  @---()_.'---@
"""


def configure_logging(level: str) -> None:
    logging.basicConfig(level=level, format=LOG_FORMAT)
    logging.getLogger("potion_lab").setLevel(level)
