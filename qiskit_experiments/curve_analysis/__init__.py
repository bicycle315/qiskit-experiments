# This code is part of Qiskit.
#
# (C) Copyright IBM 2021.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

r"""
=========================================================
Curve Analysis (:mod:`qiskit_experiments.curve_analysis`)
=========================================================

.. currentmodule:: qiskit_experiments.curve_analysis

Curve analysis provides the analysis base class for a variety of experiments with
a single experimental parameter sweep. This analysis subclasses can override
several class attributes to customize the behavior from data processing to post-processing,
including providing systematic initial guess for parameters tailored to the experiment.
Here we describe how code developers can create new analysis inheriting from the base class.


.. _curve_analysis_overview:

Curve Analysis Overview
=======================

The base class :class:`CurveAnalysis` implements the multi-objective optimization on
different sets of experiment results. A single experiment can define sub-experiments
consisting of multiple circuits which are tagged with common metadata,
and curve analysis sorts the experiment results based on the circuit metadata.

This is an example of showing the abstract data structure of typical curve analysis experiment:

.. code-block:: none
    :emphasize-lines: 1,10,19

    "experiment"
        - circuits[0] (x=x1_A, "series_A")
        - circuits[1] (x=x1_B, "series_B")
        - circuits[2] (x=x2_A, "series_A")
        - circuits[3] (x=x2_B, "series_B")
        - circuits[4] (x=x3_A, "series_A")
        - circuits[5] (x=x3_B, "series_B")
        - ...

    "experiment data"
        - data[0] (y1_A, "series_A")
        - data[1] (y1_B, "series_B")
        - data[2] (y2_A, "series_A")
        - data[3] (y2_B, "series_B")
        - data[4] (y3_A, "series_A")
        - data[5] (y3_B, "series_B")
        - ...

    "analysis"
        - "series_A": y_A = f_A(x_A; p0, p1, p2)
        - "series_B": y_B = f_B(x_B; p0, p1, p2)
        - fixed parameters {p1: v}

Here the experiment runs two subset of experiments, namely, series A and series B.
The analysis defines corresponding fit models :math:`f_A(x_A)` and :math:`f_B(x_B)`.
Data extraction function in the analysis creates two datasets, :math:`(x_A, y_A)`
for the series A and :math:`(x_B, y_B)` for the series B, from the experiment data.
Optionally, the curve analysis can fix certain parameters during the fitting.
In this example, :math:`p_1 = v` remains unchanged during the fitting.

The curve analysis aims at solving the following optimization problem:

.. math::

    \Theta_{\mbox{opt}} = \arg\min_{\Theta_{\rm fit}} \sigma^{-2} (F(X, \Theta)-Y)^2,

where :math:`F` is the composite objective function defined on the full experiment data
:math:`(X, Y)`, where :math:`X = x_A \oplus x_B` and :math:`Y = y_A \oplus y_B`.
This objective function can be described by two fit functions as follows.

.. math::

    F(X, \Theta) = f_A(x_A, \theta_A) \oplus f_B(x_B, \theta_B).

The solver conducts the least square curve fitting against this objective function
and returns the estimated parameters :math:`\Theta_{\mbox{opt}}`
that minimizes the reduced chi-squared value.
The parameters to be evaluated are :math:`\Theta = \Theta_{\rm fit} \cup \Theta_{\rm fix}`,
where :math:`\Theta_{\rm fit} = \theta_A \cup \theta_B`.
Since series A and B share the parameters in this example, :math:`\Theta_{\rm fit} = \{p_0, p_2\}`,
and the fixed parameters are :math:`\Theta_{\rm fix} = \{ p_1 \}` as mentioned.
Thus, :math:`\Theta = \{ p_0, p_1, p_2 \}`.

Experiment for each series can perform individual parameter sweep for :math:`x_A` and :math:`x_B`,
and experiment data yield outcomes :math:`y_A` and :math:`y_B`, which might be different size.
Data processing function may also compute :math:`\sigma_A` and :math:`\sigma_B` which are
the uncertainty of outcomes arising from the sampling error or measurement error.

More specifically, the curve analysis defines following data model.

- Series: Definition of the single curve. Every series may define unique
  filter keyword arguments for data sorting, a fit function with parameters,
  and preferred style for fit outcome visualization.

- Group: List of series. Fit functions defined under the group must share the
  fit parameters. Fit functions in the group are simultaneously fit to
  generate a single fit result.

To manage this structure, curve analysis provides a special dataclass :class:`SeriesDef`
that represents a model configuration for a single curve data.
Based on this information, the curve analysis automatically builds the optimization routine.
Finally, the analysis outputs a set of :class:`AnalysisResultData` entries
for important fit outcomes along with a single Matplotlib figure of the fit curves
with the measured data points.

With this baseclass a developer can avoid writing boilerplate code in
various curve analyses subclass and one can quickly write up
the analysis code for a particular experiment.


.. _curve_analysis_define_series:

Defining New Series
===================

You can intuitively write the definition of a new series, as shown below:

.. code-block:: python3

    from qiskit_experiments.curve_analysis import SeriesDef, fit_function

    SeriesDef(
        fit_func=lambda x, p0, p1, p2: fit_function.exponential_decay(
            x, amp=p0, lamb=p1, baseline=p2
        ),
        model_description="p0 * exp(-p1 * x) + p2",
    )

The minimum field you must fill with is the ``fit_func``, which is a callback function used
with the optimization solver. Here you must call one of the fit functions from the module
:mod:`qiskit_experiments.curve_analysis.fit_function` because they implement
special logic to compute error propagation.
Note that argument name of the fit function is important because
the signature of the provided fit function is inspected behind the scenes and
used as a parameter name of the analysis result instance.
This name may be used to populate your experiment database with the result.

Optionally you can set ``model_description`` which is a string representation of your
fitting model that will be passed to the analysis result as a part of metadata.
This instance should be set to :attr:`CurveAnalysis.__series__` as a python list.

Here is another example how to implement multi-objective optimization task:

.. code-block:: python3

    [
        SeriesDef(
            name="my_experiment1",
            fit_func=lambda x, p0, p1, p2, p3: fit_function.exponential_decay(
                x, amp=p0, lamb=p1, baseline=p3
            ),
            filter_kwargs={"tag": 1},
            plot_color="red",
            plot_symbol="^",
        ),
        SeriesDef(
            name="my_experiment2",
            fit_func=lambda x, p0, p1, p2, p3: fit_function.exponential_decay(
                x, amp=p0, lamb=p2, baseline=p3
            ),
            filter_kwargs={"tag": 2},
            plot_color="blue",
            plot_symbol="o",
        ),
    ]

Note that now you also need to provide ``name`` and ``filter_kwargs`` to
distinguish the entries and filter the corresponding dataset from the experiment data.
Optionally, you can provide ``plot_color`` and ``plot_symbol`` to visually
separate two curves in the plot. In this model, you have 4 parameters ``[p0, p1, p2, p3]``
and the two curves share ``p0`` (``p3``) for ``amp`` (``baseline``) of
the :func:`exponential_decay` fit function.
Here one should expect the experiment data will have two classes of data with metadata
``"tag": 1`` and ``"tag": 2`` for ``my_experiment1`` and ``my_experiment2``, respectively.

By using this model, one can flexibly set up your fit model. Here is another example:

.. code-block:: python3

    [
        SeriesDef(
            name="my_experiment1",
            fit_func=lambda x, p0, p1, p2, p3: fit_function.cos(
                x, amp=p0, freq=p1, phase=p2, baseline=p3
            ),
            filter_kwargs={"tag": 1},
            plot_color="red",
            plot_symbol="^",
        ),
        SeriesDef(
            name="my_experiment2",
            fit_func=lambda x, p0, p1, p2, p3: fit_function.sin(
                x, amp=p0, freq=p1, phase=p2, baseline=p3
            ),
            filter_kwargs={"tag": 2},
            plot_color="blue",
            plot_symbol="o",
        ),
    ]

You have the same set of fit parameters for two curves, but now you fit two datasets
with different trigonometric functions.


.. _curve_analysis_fixed_param:

Fitting with Fixed Parameters
=============================

You can also remain certain parameters unchanged during the fitting by specifying
the parameter names in the analysis option ``fixed_parameters``.
This feature is useful especially when you want to define a subclass of
a particular analysis class.

.. code-block:: python3

    class AnalysisA(CurveAnalysis):

        __series__ = [
            SeriesDef(
                fit_func=lambda x, p0, p1, p2: fit_function.exponential_decay(
                    x, amp=p0, lamb=p1, baseline=p2
                ),
            ),
        ]

    class AnalysisB(AnalysisA):

        @classmethod
        def _default_options(cls) -> Options:
            options = super()._default_options()
            options.fixed_parameters = {"p0": 3.0}

            return options

The parameter specified in ``fixed_parameters`` is exluded from the fitting.
This code will give you identical fit model to the one defined in the following class:

.. code-block:: python3

    class AnalysisB(CurveAnalysis):

        __series__ = [
            SeriesDef(
                fit_func=lambda x, p1, p2: fit_function.exponential_decay(
                    x, amp=3.0, lamb=p1, baseline=p2
                ),
            ),
        ]

However, note that you can also inherit other features, e.g. the algorithm to
generate initial guesses for parameters, from the :class:`AnalysisA` in the first example.
On the other hand, in the latter case, you need to manually copy and paste
every logic defined in the :class:`AnalysisA`.

.. _curve_analysis_workflow:

Cureve Analysis Workflow
========================

Typically curve analysis performs fitting as follows.
This workflow is defined in the method :meth:`CurveAnalysis._run_analysis`.

1. Initialization

Curve analysis calls :meth:`_initialization` method where it initializes
some internal states and optionally populate analysis options
with the input experiment data.
In some case it may train the data processor with fresh outcomes.
A developer can override this method to perform initialization of analysis-specific variables.

2. Data processing

Curve analysis calls :meth:`_run_data_processing` method where
the data processor in the analysis option is internally called.
This consumes input experiment results and creates :class:`CurveData` dataclass.
Then :meth:`_format_data` method is called with the processed dataset to format it.
By default, the formatter takes average of the outcomes in the processed dataset
over the same x values, followed by the sorting in the ascending order of x values.
This allows the analysis to easily estimate the slope of the curves to
create algorithmic initial guess of fit parameters.
A developer can inject extra data processing, for example, filtering, smoothing,
or elimination of outliers for better fitting.

3. Fitting

Curve analysis calls :meth:`_run_curve_fit` method which is the core functionality of the fitting.
The another method :meth:`_generate_fit_guesses` is internally called to
prepare the initial guess and parameter boundary with respect to the formatted data.
A developer usually override this method to provide better initial guess
tailored to the defined fit model or type of the associated experiment.
See :ref:`curve_analysis_init_guess` for more details.
A developer can also override the entire :meth:`_run_curve_fit` method to apply
custom fitting algorithms. This method must return :class:`FitData` dataclass.

4. Post processing

Curve analysis runs several postprocessing against to the fit outcome.
It calls :meth:`_create_analysis_results` to create :class:`AnalysisResultData` class
for the fitting parameters of interest. A developer can inject a custom code to
compute custom quantities based on the raw fit parameters.
See :ref:`curve_analysis_results` for details.
Afterwards, the analysis draws several curves in the Matplotlib figure.
User can set custom drawer to the option ``curve_drawer``.
The drawer defaults to the :class:`MplCurveDrawer`.
Finally, it returns the list of created analysis results and Matplotlib figure.


.. _curve_analysis_init_guess:

Providing Initial Guesses
=========================

When fit is performed without any prior information of parameters, it usually
falls into unsatisfactory result.
User can provide initial guesses and boundaries for the fit parameters
through analysis options ``p0`` and ``bounds``.
These values are the dictionary keyed on the parameter name,
and one can get the list of parameters with the :attr:`CurveAnalysis.parameters`.
Each boundary value can be a tuple of float representing min and max value.

Apart from user provided guesses, the analysis can systematically generate
those values with the method :meth:`_generate_fit_guesses` which is called with
:class:`CurveData` dataclass. If the analysis contains multiple series definitions,
we can get the subset of curve data with :meth:`CurveData.get_subset_of` with
the name of the series.
A developer can implement the algorithm to generate initial guesses and boundaries
by using this curve data object, which will be provided to the fitter.
Note that there are several common initial guess estimators available in
:mod:`qiskit_experiments.curve_analysis.guess`.

The :meth:`_generate_fit_guesses` also receives :class:`FitOptions` instance ``user_opt``,
which contains user provided guesses and boundaries.
This is dictionary-like object consisting of sub-dictionaries for
initial guess ``.p0``, boundary ``.bounds``, and extra options for the fitter.
Note that :class:`CurveAnalysis` uses SciPy `curve_fit`_ as the least square solver.
See the API documentation for available options.

The :class:`FitOptions` class implements convenient method :meth:`set_if_empty` to manage
conflict with user provided values, i.e. user provided values have higher priority,
thus systematically generated values cannot override user values.

.. code-block:: python3

    def _generate_fit_guesses(self, user_opt, curve_data):

        opt1 = user_opt.copy()
        opt1.p0.set_if_empty(p1=3)
        opt1.bounds = set_if_empty(p1=(0, 10))
        opt1.add_extra_options(method="lm")

        opt2 = user_opt.copy()
        opt2.p0.set_if_empty(p1=4)

        return [opt1, opt2]

Here you created two options with different ``p1`` values.
If multiple options are returned like this, the :meth:`_run_curve_fit` method
attempts to fit with all provided options and finds the best outcome with
the minimum reduced chi-square value.
When the fit model contains some parameter that cannot be easily estimated from the
curve data, you can create multiple options with varying the initial guess to
let the fitter find the most reasonable parameters to explain the model.
This allows you to avoid analysis failure with the poor initial guesses.

.. _curve_fit: https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.curve_fit.html


.. _curve_analysis_quality:

Evaluate Fit Quality
====================

A subclass can override :meth:`_evaluate_quality` method to
provide an algorithm to evaluate quality of the fitting.
This method is called with the :class:`FitData` object which contains
fit parameters and the reduced chi-squared value.
Qiskit Experiments often uses the empirical criterion chi-squared < 3 as a good fitting.


.. _curve_analysis_results:

Curve Analysis Results
======================

Once the best fit parameters are found, the :meth:`_create_analysis_results` method is
called with the same :class:`FitData` object.
By default :class:`CurveAnalysis` only creates a single entry ``@Parameters_<name_of_analysis>``.
This entry consists of fit parameter values with statistical information of the fitting.

If you want to create an analysis result entry for the particular parameter,
you can override the analysis options ``result_parameters``.
By using :class:`ParameterRepr` representation, you can rename the parameter in the entry.

.. code-block:: python3

    from qiskit_experiments.curve_analysis import ParameterRepr

    def _default_options(cls) -> Options:
        options = super()._default_options()
        options.result_parameters = [ParameterRepr("p0", "amp", "Hz")]

        return options

Here the first argument ``p0`` is the target parameter defined in the series definition,
``amp`` is the representation of ``p0`` in the result entry,
and ``Hz`` is the optional string for the unit of the value if available.

Not only returning the fit parameters, you can also compute new quantities
by combining multiple fit parameters.
This can be done by overriding the :meth:`_create_analysis_results` method.

.. code-block:: python3

    from qiskit_experiments.framework import AnalysisResultData

    def _create_analysis_results(self, fit_data, quality, **metadata):

        outcomes = super()._create_analysis_results(fit_data, **metadata)

        p0 = fit_data.fitval("p0")
        p1 = fit_data.fitval("p1")

        extra_entry = AnalysisResultData(
            name="p01",
            value=p0 * p1,
            quality=quality,
            extra=metadata,
        )
        outcomes.append(extra_entry)

        return outcomes

Note that both ``p0`` and ``p1`` are `ufloat`_ object consisting of
a nominal value and an error value which assumes the standard deviation.
Since this object natively supports error propagation,
you don't need to manually recompute the error of new value.

.. _ufloat: https://pythonhosted.org/uncertainties/user_guide.html


If there is any missing feature, you can write a feature request as an issue in our
`GitHub <https://github.com/Qiskit/qiskit-experiments/issues>`_.


Base Classes
============

.. autosummary::
    :toctree: ../stubs/

    BaseCurveAnalysis
    CurveAnalysis

Data Classes
============

.. autosummary::
    :toctree: ../stubs/

    SeriesDef
    CurveData
    FitData
    ParameterRepr
    FitOptions

Visualization
=============

.. autosummary::
    :toctree: ../stubs/

    BaseCurveDrawer
    MplCurveDrawer

Standard Analysis Library
=========================

.. autosummary::
    :toctree: ../stubs/
    :template: autosummary/analysis.rst

    DecayAnalysis
    DumpedOscillationAnalysis
    OscillationAnalysis
    ResonanceAnalysis
    GaussianAnalysis
    ErrorAmplificationAnalysis

Fit Functions
*************
.. autosummary::
    :toctree: ../stubs/

    fit_function.cos
    fit_function.cos_decay
    fit_function.exponential_decay
    fit_function.gaussian
    fit_function.sqrt_lorentzian
    fit_function.sin
    fit_function.sin_decay
    fit_function.bloch_oscillation_x
    fit_function.bloch_oscillation_y
    fit_function.bloch_oscillation_z

Initial Guess Estimators
************************
.. autosummary::
    :toctree: ../stubs/

    guess.constant_sinusoidal_offset
    guess.constant_spectral_offset
    guess.exp_decay
    guess.rb_decay
    guess.full_width_half_max
    guess.frequency
    guess.max_height
    guess.min_height
    guess.oscillation_exp_decay

Utilities
*********
.. autosummary::
    :toctree: ../stubs/

    is_error_not_significant
"""
from .base_curve_analysis import BaseCurveAnalysis
from .curve_analysis import CurveAnalysis, is_error_not_significant
from .curve_data import CurveData, SeriesDef, FitData, ParameterRepr, FitOptions
from .curve_fit import (
    curve_fit,
    multi_curve_fit,
    process_curve_data,
    process_multi_curve_data,
)
from .visualization import BaseCurveDrawer, MplCurveDrawer
from . import guess
from . import fit_function

# standard analysis
from .standard_analysis import (
    DecayAnalysis,
    DumpedOscillationAnalysis,
    OscillationAnalysis,
    ResonanceAnalysis,
    GaussianAnalysis,
    ErrorAmplificationAnalysis,
)

# deprecated
from .visualization import plot_curve_fit, plot_errorbar, plot_scatter, FitResultPlotters
