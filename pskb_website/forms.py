from flask_wtf import Form
from wtforms import StringField, SelectMultipleField, validators

STACK_OPTIONS = ('Java and J2EE',
                 'C/C++',
                 'Python',
                 'PHP',
                 'Ruby, Ruby on Rails',
                 'Node.js',
                 'SQL',
                 'HTML/CSS',
                 'Lua',
                 'Go',
                 'Scala',
                 'Haskell',
                 'Clojure',
                 'Erlang',
                 'Objective C',
                 'Swift',
                 'Software Engineering Best Practices',
                 'Microsoft.NET (C#, ASP.NET, VB.NET, etc)',
                 'Big Data (Hadoop, Spark, etc)',
                 'NoSQL Databases (MongoDB, Cassandra, etc)',
                 'Interesting APIs (SendGrid, Twilio, etc)',
                 'Front-End JavaScript (Angular, React, Meteor, etc)',
                 'DevOps (Docker, Nagios, Jenkins, Chef, Puppet, etc)',
                 'Android')


class SignupForm(Form):
    email = StringField('Email', [
        validators.required(),
        validators.Email(message=(u'Please enter a valid email address.')),
    ])
    stacks = SelectMultipleField('Stacks', choices=[(s, s) for s in STACK_OPTIONS])
