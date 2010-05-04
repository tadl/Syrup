% DRAFT: Interface specification for an OpenSRF campus-information service
% Graham Fawcett
% March 26, 2010

# Introduction

This document specifies the interface for an OpenSRF-based service
which gives OpenSRF applications access to *campus information*, such
as the names of courses taught at a given university, who is teaching
them, and which students are enrolled in them.

This service is designed to meet the needs of our reserves
application, "Syrup." We hope the service will be useful in a wide
range of library applications that could benefit from access to course-related
information.

This document specifies the OpenSRF interface of the campus
information service, but it does not dictate how the service must be
implemented. Each institution will need to implement the service,
using the tools of their choice, in a way that makes local sense.

# Design considerations

## Partial implementations

In an ideal world, a library would have unlimited access to all the
course-related information they wanted; but many libraries do not
enjoy such access. Not all applications need the same types of
information, and many applications can adapt to different levels of
available campus information. Given this, it is acceptable to
*partially* implement the campus-information service, skipping the
parts that you cannot (or choose not to) implement.

For example, if you don't have access to any class-list information,
but you do have a machine-readable version of the academic calendar,
you could implement the course-lookup and term-lookup parts of the
interface, but skip the course-offering parts.

An application must be able to determine what parts of the interface
you have implemented. Therefore, you must implement the
`methods-supported` method (see [Static informational methods]). Since
this method-list is essentially static (it will change only if you
modify your implementation), an application may test it infrequently,
e.g. just once upon startup.

## Caching

OpenSRF provides a high-performance caching framework. You should
consider using this framework when designing your
implementation. 

Applications are discouraged from caching campus information:
especially information on people and course offerings, which both
change relatively frequently. It makes more sense to centralize policy
decisions about the lifespans of campus data at the service layer.  If
applications must cache campus information (e.g. for demonstrated
performance reasons), they are encouraged to keep the cache-lifetimes
as short as possible.

# Data types

All of these data types are needed in a complete implementation of the
interface. Since you are free to implement only parts of the interface
(see [Partial implementations]), all of these data types might not
apply in your case.

## Identifier types

    COURSE-ID   = string        (matching a local COURSE-ID-FORMAT)
    TERM-ID     = string        (matching a local TERM-ID-FORMAT)
    OFFERING-ID = string        (matching a local OFFERING-ID-FORMAT)
    PERSON-ID   = string        (matching a local PERSON-ID-FORMAT)

The four identifier types are used respectively as unique keys for
courses, terms, course offerings, and people. (`String` is the
primitive type of strings of Unicode characers.)

Since the PERSON-ID may be exposed in reports and user interfaces, it
should be a common public identifier (such as a 'single-sign-on ID',
'email prefix', or 'campus username') that can be displayed beside the
person's name without violating privacy regulations.

Your institution may use 'section numbers' to differentiate multiple
offerings of a course in the same term. You may embed them in your
identifiers: for example, the offering ID `ENG100-2010W-03` might
represent Section 3 of English 100 being taught in Winter 2010. But it
isn't required that your offering IDs are so structured.

**Formats:** Each type of identifier complies with a respective,
locally-defined format. You should define a (private, internal)
function for each format, that verifies whether a given string matches
the format. For example, a Java implementation might define a
function, `boolean isValidCourseID(String)`. You might use regular
expressions to define your formats, but it's not a requirement. At the
very least, your local formats should reject empty strings as IDs. You
may expose these functions for application use: see
[Format-matching methods].

## Record types

Record types are modelled as associative arrays (sets of key/value
pairs). \[Is this acceptable in OpenSRF? It's valid JSON, but I'm not clear on OpenSRF conventions.\]
The following notation is used in the type definitions:

             string            (a string primitive)
             [string]*         (an unordered set of zero or more strings)
             (string)?         (an optional string: it may be NULL.)

Strictly, unordered sets *do* have an order, since they are
implemented as JSON lists. But the specification does not guarantee
that the order of the list is significant. 

Missing optional values may be indicated in two equivalent ways:
either include the key, and pair it with a `null` value (`{key: null,
...}`), or simply omit the key/value pair from the record.
               
    COURSE = { id:    COURSE-ID, 
               title: string }

A COURSE record describes a course in the abstract sense, as it would
appear in an academic calendar. It must have at least a unique course
ID and a descriptive (possibly non-unique) title. It may include other
attributes if you wish, but we specify `id` and `title` as required
attributes.

    TERM = { id:         TERM-ID, 
             name:       string, 
             start-date: date, 
             end-date:   date }

A TERM record describes a typical period in which a course is offered
(a 'term' or 'semester'). It must have a unique term-ID, a
probably-unique name, and start and end dates. (`Date` is a primitive
type, representing a calendar date.)

    PERSON = { id:         PERSON-ID, 
               surname:    string, 
               given-name: string,
               email:      (string)? }

A PERSON record describes a person! It must include a unique
person-ID, a surname and given name. A value for `email` is
optional. You may also add other attributes as you see fit.
                 
    OFFERING = { id:            OFFERING-ID,
                 course:        COURSE-ID,
                 starting-term: TERM-ID,
                 ending-term:   TERM-ID,
                 students:      [PERSON-ID]*,
                 assistants:    [PERSON-ID]*,
                 instructors:   [PERSON-ID]* }

An OFFERING record describes a course offering: your institution might
call this a 'class' or a 'section'.  It has specific start- and and
end-dates (derived from its starting and ending terms: some
institutions have courses that span multiple terms). The `course`
attribute refers to the single course of which it is an instance (our
specification punts on the issue of cross-listed offerings).  It has
unordered sets of zero-or-more students, teaching assistants and
instructors.

Each OFFERING record is a snapshot of a course offering at a given
time. It is assumed that people may join or leave the course
offering at any point during its duration.

The set of "assistants" is loosely defined. It might include teaching
assistants (TAs and GAs) but also technical assistants, departmental
support staff, and other ancillary support staff.

    OFFERING-FLESHED = { id:            OFFERING-ID,
                         course:        COURSE,
                         starting-term: TERM,
                         ending-term:   TERM,
                         students:      [PERSON]*,
                         assistants:    [PERSON]*,
                         instructors:   [PERSON]* }

A OFFERING-FLESHED record is like an OFFERING record, except that the
course, term, and people-set attributes have been 'fleshed out', so
that they contain not codes, but actual copies of the COURSE, TERM and
PERSON records.

# Method signatures

The following notation is used for method signatures:

    method-name:   arg1-type, ... argN-type -> result-type
    
The `void` type is used to express empty argument-lists.

## Static informational methods

    methods-supported:   void      -> [string]*

The `methods-supported` method is the only method that you *must*
implement (see [Partial implementations]). It returns a list of the
names of the methods for which you've provided
implementations. Applications can use this list to determine the
capabilities of your implementation.
    
## Course methods

    course-lookup:       COURSE-ID -> (COURSE)?
    course-id-list:      void      -> [COURSE-ID]*
    course-list:         void      -> [COURSE]*
    course-id-example:   void      -> (COURSE-ID)?

Given a COURSE-ID string, `course-lookup` will return the matching
COURSE record, or `null` if no such course exists. 

The methods `course-id-list` and `course-list` return a list of the
IDs (or records, respectively) of *all* known courses in the campus
system. An application might use these to populate option-lists or
report headings. The lists may be limited to the courses which are
defined in the current academic calendar (that is, your implementation
may omit obsolete course descriptions).

The `course-id-example` method returns a course ID *example*. In
user-interfaces where a course ID must be typed in, this example can
be used to offer some guidance to the user. If the method returns
`null`, or if the method is not implemented, an application should
simply omit any example from the user interface.

## Term methods

    term-lookup:         TERM-ID   -> (TERM)?
    term-list:           void      -> [TERM]*
    terms-at-date:       date      -> [TERM]*

The `term-lookup` and `term-list` are analogous to the `course-lookup`
and `course-list` methods. The `terms-at-date` method takes a date
argument, and returns a list of all TERM records such that `term.start
<= date <= term.finish`. (We do not specify that terms are
non-overlapping.)

## Person methods

    person-lookup:       PERSON-ID   -> (PERSON)?

## Offering methods

To describe the return-values of some of the Offering methods, we
introduce the notation `MBR(X)` as an abbreviation for the type
`([X]*, [X]*, [X]*)`, that is, a trio of sets representing the three
membership groups associated with a course offering: teachers,
assistants, and students. The types of elements contained in the sets
is specified by the specializing type, `X`: so, `MBR(PERSON)` is a
trio of sets of PERSON records.

    MBR(TYPE) = ([TYPE]*,  # memberships as a teacher,
                 [TYPE]*,  # as an assistant,
                 [TYPE]*)  # as a student.


    course-term-offerings:         (COURSE-ID, TERM-ID) -> [OFFERING]*
    course-term-offerings-fleshed: (COURSE-ID, TERM-ID) -> [OFFERING-FLESHED]*

Given a COURSE-ID and a TERM-ID, these methods will return records for
all course offerings for the course represented by COURSE-ID, whose
`starting-term` *or* `ending-term` is equal to TERM-ID.

    memberships:         PERSON-ID    -> MBR(OFFERING)
    membership-ids:      PERSON-ID    -> MBR(OFFERING-ID)
    memberships-fleshed: PERSON-ID    -> MBR(OFFERING-FLESHED)
    
These methods take a PERSON-ID and return a trio of sets whose
elements represent the course-offerings in which the person is
(respectively) a teacher, assistant, or student. 

Within a given course-offering, a person must belong to no more than
one of the three sets. For example, it is not permitted to be both a
teacher and student for the same offering. 

If the PERSON-ID is invalid, or if the person is not a member of any
offerings, the return value should be a trio of three empty sets --
`[[], [], []]` -- *not* a `null` value or an error.

    member-ids:          OFFERING-ID -> MBR(PERSON-ID)
    members:             OFFERING-ID -> MBR(PERSON)
    
These methods take an OFFERING-ID and return a trio of sets whose
elements represent (respectively) the teachers, assistants, and
students in the offering. 

If the OFFERING-ID is invalid, or if the offering is "empty", the
return value should be a trio of three empty sets -- `[[], [], []]` --
*not* a `null` value or an error.

    teacher-ids:         OFFERING-ID -> ([PERSON-ID]*, [PERSON-ID]*)
    teachers:            OFFERING-ID -> ([PERSON]*, [PERSON]*)


The `teacher` methods are identical to the `member` methods, except
that the student set is omitted: the return-value is a *pair* of sets
representing teachers and assistants. These are essentially optimized
versions of the `members` methods for cases when you only need to know
about the teaching and support teams (typically, very small groups)
and can avoid the cost of calculating and transmitting the student list
(typically, 10-100 times larger).

## Format-matching methods

    resembles-course-id:   string    -> boolean
    resembles-offering-id: string    -> boolean
    resembles-term-id:     string    -> boolean
    resembles-person-id:   string    -> boolean
    
Applications can use these to implement data-input validation tests in
user interfaces, primarily where lookups are not possible. They
determine whether a given string falls within the general guidelines
of what your IDs are supposed to look like. At some institutions, this
might be the best you can offer: you might not have access to
databases in which you can look records up, but at least you can offer
a means to avoid basic typographic errors.

You could implement these methods by exposing the functions you
defined for your COURSE-ID-FORMAT, TERM-ID-FORMAT, OFFERING-ID-FORMAT
and PERSON-ID-FORMAT tests (see [Identifier types]). At the least,
these formats should ensure that empty strings are rejected.

You might choose to use implement these as lookup functions, returning
`true` only if a matching record was found. For example, if your
school offers only two courses (say, `ENG100` and `ENG200`), you could
choose to implement a `resembles-course-id` method that only returned
`true` if the argument was exactly one of those two course codes.  No
matter how you implement it, the intent of the `resembles` methods is
to help avoid typographic errors, not to act as a membership test.

[Partial implementations]: #partial-implementations
[Static informational methods]: #static-informational-methods
[Identifier types]: #identifier-types
[Format-matching methods]: #format-matching-methods

<!-- 
Local Variables:
mode: markdown
End: 
-->
