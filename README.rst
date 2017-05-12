Address Parser
==============

Yet another python address parser for US postal addresses

Basic usage:

.. code-block:: python

    from address_parser import Parser

    parser = Parser()
    adr = parser.parse(line)

The ``adr`` object is a nested object with address parts as properties.

.. code-block:: python

    return TopBunch(
            number=Bunch(
                type='P',
                number=int(self.number) if self.number else -1,
                tnumber=str(self.number),
                end_number=self.multinumber,
                fraction=self.fraction,
                suite=self.suite,
                is_block=self.is_block
            ),

            road=Bunch(
                type='P',
                name=self.street_name,
                direction=self.street_direction if self.street_direction else '',
                suffix=self.street_type if self.street_type else ''
            ),

            locality=Bunch(
                type='P',
                city=self.city,
                state=self.state,
                zip=self.zip

            ),

            hash=self.hash,

            text=str(self)
        )


Then, you can access properties on the object. The top level properties are:

- number: The house number
    - number.number. The number as an integer, or -1 if there is no house number
    - number.tnumber: The number as text
    - number.end_number: The final number in a number rage
    - number.fraction: The fractional part of the house number
    - number.suite: A suite or unit number.
- road: The street
    - road.name: The bare street name
    - road.direction. A cardinal direction, N, S, E, W, NE, NW, etc.
    - road.suffix. The road type, sich as St, Ave, Pl.
- locality: City, state, zip
    - locality.city
    - locality.state
    - locality.zip
- text: Holds the whole address as text.

You can also access everything as dicts. From the top level, ``adr.dict`` will return all parsed components as a dict, and each of the top level bunches can also be acess as dicts, such as ``adr.road.dict``

