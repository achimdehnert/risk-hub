DSB Models
==========

Lookup Models
-------------

TomCategory
~~~~~~~~~~~

Classifies TOM measures into categories with a measure type.

.. list-table::
   :header-rows: 1
   :widths: 25 25 50

   * - Field
     - Type
     - Description
   * - ``key``
     - CharField(50)
     - Unique category identifier
   * - ``name``
     - CharField(200)
     - Display name
   * - ``measure_type``
     - CharField(20)
     - One of: ``technical``, ``organizational``, ``avv``
   * - ``description``
     - TextField
     - Optional description
   * - ``is_active``
     - BooleanField
     - Soft-disable flag

MeasureType Choices
~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   class MeasureType(models.TextChoices):
       TECHNICAL = "technical", "Technisch"
       ORGANIZATIONAL = "organizational", "Organisatorisch"
       AVV = "avv", "AVV"

Management Commands
-------------------

seed_tom_categories
~~~~~~~~~~~~~~~~~~~

Populates the ``TomCategory`` table with default categories.

.. code-block:: bash

   python manage.py seed_tom_categories

This is idempotent — running it multiple times will not create duplicates
(uses ``update_or_create`` on the ``key`` field).
