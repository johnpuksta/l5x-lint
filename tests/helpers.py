"""Shared test helpers for building minimal L5X XML."""

from returns.result import Failure, Success

from l5x_lint.infrastructure.adapter import parse_l5x
from l5x_lint.application.analyze import analyze


def minimal_l5x(controller_content="", software_revision="32.00"):
    """Build a minimal valid L5X XML string."""
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<RSLogix5000Content SchemaRevision="1.0" SoftwareRevision="{software_revision}">
  <Controller Name="Test" ProcessorType="1756-L83E">
    {controller_content}
  </Controller>
</RSLogix5000Content>'''


def l5x_with_rll(routine_name, rll_code):
    """Build minimal L5X with one RLL routine containing the given code."""
    return minimal_l5x(f"""
    <DataTypes/><Tags/>
    <Programs><Program Name="Main">
      <Tags/>
      <Routines>
        <Routine Name="{routine_name}" Type="RLL">
          <RLLContent><Rung Number="0"><Text>{rll_code}</Text></Rung></RLLContent>
        </Routine>
      </Routines>
    </Program></Programs>
    <Tasks/>
    <AddOnInstructionDefinitions/>
    <Modules/>""")


def l5x_with_st(routine_name, st_code):
    """Build minimal L5X with one ST routine containing the given code."""
    return minimal_l5x(f"""
    <DataTypes/><Tags/>
    <Programs><Program Name="Main">
      <Tags/>
      <Routines>
        <Routine Name="{routine_name}" Type="ST">
          <STContent><Line Number="0">{st_code}</Line></STContent>
        </Routine>
      </Routines>
    </Program></Programs>
    <Tasks/>
    <AddOnInstructionDefinitions/>
    <Modules/>""")


def parse_and_analyze(xml):
    """Parse L5X then run analyze (which triggers RLL/ST parsing)."""
    result = parse_l5x(xml)
    if isinstance(result, Failure):
        return result
    project = result.unwrap()
    return analyze(project.controller)
